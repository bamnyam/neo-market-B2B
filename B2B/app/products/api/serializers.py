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
    title = serializers.CharField(min_length=1, max_length=255)
    description = serializers.CharField(min_length=1, max_length=5000)
    category_id = serializers.UUIDField()
    images = ProductImageCreateSerializer(many=True)
    characteristics = ProductCharacteristicCreateSerializer(many=True, required=False)

    def validate_images(self, value):
        if not value:
            raise serializers.ValidationError("At least one image is required")

        return value

    def validate_category_id(self, value):
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError("Category not found")

        return value

    def create(self, validated_data):
        seller = self.context["seller"]
        images_data = validated_data.pop("images")
        characteristics_data = validated_data.pop("characteristics", [])
        category_id = validated_data.pop("category_id")

        product = Product.objects.create(
            seller=seller,
            category_id=category_id,
            status=ProductStatus.CREATED,
            **validated_data,
        )

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


class ProductResponseSerializer(serializers.ModelSerializer):
    seller_id = serializers.UUIDField(source="seller.id")
    category_id = serializers.UUIDField(source="category.id")

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
            "description",
            "status",
            "images",
            "characteristics",
            "skus",
            "created_at",
            "updated_at",
        ]

    def get_images(self, obj):
        return [
            {
                "id": str(image.id),
                "url": image.url,
                "ordering": image.ordering,
            }
            for image in obj.images.all().order_by("ordering")
        ]

    def get_characteristics(self, obj):
        return [
            {
                "id": str(characteristic.id),
                "name": characteristic.name,
                "value": characteristic.value,
            }
            for characteristic in obj.characteristics.all()
        ]

    def get_skus(self, obj):
        return [
            {
                "id": str(sku.id),
                "name": sku.name,
                "price": sku.price,
                "stock_quantity": sku.stock_quantity,
                "article": sku.article,
            }
            for sku in obj.skus.all()
        ]
