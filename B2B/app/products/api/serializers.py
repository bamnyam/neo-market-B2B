from django.db import transaction
from rest_framework import serializers

from app.categories.models import Category
from app.products.models import (
    Product,
    ProductStatus,
    ProductImages,
    ProductCharacteristics,
)


class ProductImageCreateSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=255)
    ordering = serializers.IntegerField(min_value=0)


class ProductCharacteristicCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255)


class ProductCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    slug = serializers.SlugField(
        min_length=1,
        max_length=255,
    )

    description = serializers.CharField(
        min_length=1,
        max_length=5000,
    )

    category_id = serializers.UUIDField()

    images = ProductImageCreateSerializer(
        many=True,
        required=True,
        min_length=1,
    )

    characteristics = ProductCharacteristicCreateSerializer(
        many=True,
        required=False,
        default=list,
    )

    def validate_category_id(self, value):

        if not Category.objects.filter(uuid=value).exists():
            raise serializers.ValidationError("Category not found")

        return value

    def validate_slug(self, value):

        if Product.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Slug already exists")

        return value

    def validate_images(self, value):

        orderings = [image["ordering"] for image in value]

        if len(orderings) != len(set(orderings)):
            raise serializers.ValidationError("Image ordering must be unique")

        return value

    @transaction.atomic
    def create(self, validated_data):

        seller = self.context["seller"]

        images_data = validated_data.pop(
            "images",
            [],
        )

        characteristics_data = validated_data.pop(
            "characteristics",
            [],
        )

        category_uuid = validated_data.pop("category_id")

        category = Category.objects.get(uuid=category_uuid)

        product = Product.objects.create(
            seller=seller,
            category=category,
            status=ProductStatus.CREATED,
            deleted=False,
            **validated_data,
        )

        if images_data:
            ProductImages.objects.bulk_create(
                [
                    ProductImages(
                        product=product,
                        url=image["url"],
                        ordering=image["ordering"],
                    )
                    for image in images_data
                ]
            )

        if characteristics_data:
            ProductCharacteristics.objects.bulk_create(
                [
                    ProductCharacteristics(
                        product=product,
                        name=characteristic["name"],
                        value=characteristic["value"],
                    )
                    for characteristic in characteristics_data
                ]
            )

        return product


class ProductUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(
        min_length=1,
        max_length=255,
        required=False,
    )

    slug = serializers.SlugField(
        min_length=1,
        max_length=255,
        required=False,
    )

    description = serializers.CharField(
        min_length=1,
        max_length=5000,
        required=False,
    )

    category_id = serializers.UUIDField(
        required=False,
    )

    images = ProductImageCreateSerializer(
        many=True,
        required=False,
        min_length=1,
    )

    characteristics = ProductCharacteristicCreateSerializer(
        many=True,
        required=False,
    )

    def validate_category_id(self, value):

        if not Category.objects.filter(uuid=value).exists():
            raise serializers.ValidationError("Category not found")

        return value

    def validate_slug(self, value):
        product = self.context["product"]

        if Product.objects.filter(slug=value).exclude(id=product.id).exists():
            raise serializers.ValidationError("Slug already exists")

        return value

    def validate_images(self, value):

        orderings = [image["ordering"] for image in value]

        if len(orderings) != len(set(orderings)):
            raise serializers.ValidationError("Image ordering must be unique")

        return value


class ProductResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(
        source="uuid",
        read_only=True,
    )

    seller_id = serializers.UUIDField(
        source="seller.uuid",
        read_only=True,
    )

    category_id = serializers.UUIDField(
        source="category.uuid",
        read_only=True,
    )

    images = serializers.SerializerMethodField()

    characteristics = serializers.SerializerMethodField()

    skus = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = [
            "id",
            "seller_id",
            "category_id",
            "title",
            "slug",
            "description",
            "status",
            "deleted",
            "blocking_reason_id",
            "moderator_comment",
            "images",
            "characteristics",
            "skus",
            "created_at",
            "updated_at",
        ]

    def get_images(self, obj):

        return [
            {
                "id": str(image.uuid),
                "url": image.url,
                "ordering": image.ordering,
            }
            for image in obj.images.all().order_by("ordering")
        ]

    def get_characteristics(self, obj):

        return [
            {
                "id": str(characteristic.uuid),
                "name": characteristic.name,
                "value": characteristic.value,
            }
            for characteristic in obj.characteristics.all()
        ]

    def get_skus(self, obj):

        return [
            {
                "id": str(sku.uuid),
                "product_id": str(obj.uuid),
                "name": sku.name,
                "price": float(sku.price),
                "discount": float(sku.discount),
                "cost_price": float(sku.cost_price),
                "stock_quantity": sku.stock_quantity,
                "active_quantity": sku.active_quantity,
                "reserved_quantity": sku.reserved_quantity,
                "article": sku.article,
                "images": [
                    {
                        "id": str(image.uuid),
                        "url": image.url,
                        "ordering": image.ordering,
                    }
                    for image in sku.images.all().order_by("ordering")
                ],
                "characteristics": [
                    {
                        "id": str(characteristic.uuid),
                        "name": characteristic.name,
                        "value": characteristic.value,
                    }
                    for characteristic in sku.characteristics.all()
                ],
                "created_at": sku.created_at,
                "updated_at": sku.updated_at,
            }
            for sku in obj.skus.all()
        ]


class ProductListItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(
        source="uuid",
        read_only=True,
    )

    category_id = serializers.UUIDField(
        source="category.uuid",
        read_only=True,
    )

    min_price = serializers.SerializerMethodField()

    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "category_id",
            "deleted",
            "created_at",
            "min_price",
            "cover_image",
        ]

    def get_min_price(self, obj):
        prices = [sku.price for sku in obj.skus.all()]

        if not prices:
            return None

        return float(min(prices))

    def get_cover_image(self, obj):
        image = next(
            iter(obj.images.all().order_by("ordering")),
            None,
        )

        if image is None:
            return None

        return image.url
