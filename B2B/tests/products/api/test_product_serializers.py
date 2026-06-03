# tests/products/api/test_product_serializers.py

import uuid

import pytest

from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductListItemSerializer,
    ProductResponseSerializer,
)
from app.products.models import (
    Product,
    ProductCharacteristics,
    ProductImages,
    ProductStatus,
)
from app.skus.models import Sku
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.mark.django_db
def test_product_create_serializer_creates_product_with_images_and_characteristics():
    seller = SellerFactory()
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "slug": "iphone",
            "description": "desc",
            "category_id": str(category.uuid),
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
            "characteristics": [
                {
                    "name": "brand",
                    "value": "Apple",
                }
            ],
        },
        context={"seller": seller},
    )

    assert serializer.is_valid(), serializer.errors

    product = serializer.save()

    assert product.seller == seller
    assert product.category == category
    assert product.title == "iPhone"
    assert product.slug == "iphone"
    assert product.description == "desc"
    assert product.status == ProductStatus.CREATED
    assert product.deleted is False

    assert Product.objects.count() == 1
    assert ProductImages.objects.count() == 1
    assert ProductCharacteristics.objects.count() == 1

    image = ProductImages.objects.first()

    assert image.product == product
    assert image.url == "/s3/image.jpg"
    assert image.ordering == 0

    characteristic = ProductCharacteristics.objects.first()

    assert characteristic.product == product
    assert characteristic.name == "brand"
    assert characteristic.value == "Apple"


@pytest.mark.django_db
def test_product_create_serializer_rejects_missing_images():
    seller = SellerFactory()
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "slug": "iphone-without-images",
            "description": "desc",
            "category_id": str(category.uuid),
        },
        context={"seller": seller},
    )

    assert not serializer.is_valid()
    assert "images" in serializer.errors

    assert Product.objects.count() == 0
    assert ProductImages.objects.count() == 0
    assert ProductCharacteristics.objects.count() == 0


@pytest.mark.django_db
def test_product_create_serializer_generates_slug_when_missing():
    seller = SellerFactory()
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone 15",
            "description": "desc",
            "category_id": str(category.uuid),
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
        },
        context={"seller": seller},
    )

    assert serializer.is_valid(), serializer.errors

    product = serializer.save()

    assert product.slug == "iphone-15"


@pytest.mark.django_db
def test_product_create_serializer_generates_unique_slug_when_missing():
    seller = SellerFactory()
    category = CategoryFactory()
    Product.objects.create(
        seller=seller,
        category=category,
        title="Old iPhone",
        slug="iphone",
        description="old desc",
        status=ProductStatus.CREATED,
    )

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "description": "desc",
            "category_id": str(category.uuid),
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
        },
        context={"seller": seller},
    )

    assert serializer.is_valid(), serializer.errors

    product = serializer.save()

    assert product.slug == "iphone-1"


@pytest.mark.django_db
def test_product_create_serializer_rejects_missing_category():
    seller = SellerFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "slug": "iphone",
            "description": "desc",
            "category_id": str(uuid.uuid4()),
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
        },
        context={"seller": seller},
    )

    assert not serializer.is_valid()
    assert "category_id" in serializer.errors


@pytest.mark.django_db
def test_product_create_serializer_rejects_duplicate_slug():
    seller = SellerFactory()
    category = CategoryFactory()

    Product.objects.create(
        seller=seller,
        category=category,
        title="Old iPhone",
        slug="iphone",
        description="old desc",
        status=ProductStatus.CREATED,
    )

    serializer = ProductCreateSerializer(
        data={
            "title": "New iPhone",
            "slug": "iphone",
            "description": "new desc",
            "category_id": str(category.uuid),
        },
        context={"seller": seller},
    )

    assert not serializer.is_valid()
    assert "slug" in serializer.errors


@pytest.mark.django_db
def test_product_create_serializer_rejects_duplicate_image_ordering():
    seller = SellerFactory()
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "slug": "iphone",
            "description": "desc",
            "category_id": str(category.uuid),
            "images": [
                {
                    "url": "/s3/1.jpg",
                    "ordering": 0,
                },
                {
                    "url": "/s3/2.jpg",
                    "ordering": 0,
                },
            ],
        },
        context={"seller": seller},
    )

    assert not serializer.is_valid()
    assert "images" in serializer.errors


@pytest.mark.django_db
def test_product_response_serializer_returns_expected_payload():
    seller = SellerFactory()
    category = CategoryFactory()

    product = Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone",
        slug="iphone",
        description="desc",
        status=ProductStatus.CREATED,
    )

    image = ProductImages.objects.create(
        product=product,
        url="/s3/image.jpg",
        ordering=0,
    )

    characteristic = ProductCharacteristics.objects.create(
        product=product,
        name="brand",
        value="Apple",
    )

    sku = Sku.objects.create(
        product=product,
        name="iPhone 128GB",
        price=100000,
        discount=10000,
        cost_price=80000,
        stock_quantity=10,
        active_quantity=8,
        reserved_quantity=2,
        article="iphone-128gb",
    )

    data = ProductResponseSerializer(product).data

    assert data["id"] == str(product.uuid)
    assert data["seller_id"] == str(seller.uuid)
    assert data["category_id"] == str(category.uuid)

    assert data["title"] == "iPhone"
    assert data["slug"] == "iphone"
    assert data["description"] == "desc"
    assert data["status"] == ProductStatus.CREATED
    assert data["deleted"] is False
    assert data["blocking_reason_id"] is None
    assert data["moderator_comment"] is None

    assert data["created_at"] is not None
    assert data["updated_at"] is not None

    assert data["images"] == [
        {
            "id": str(image.uuid),
            "url": "/s3/image.jpg",
            "ordering": 0,
        }
    ]

    assert data["characteristics"] == [
        {
            "id": str(characteristic.uuid),
            "name": "brand",
            "value": "Apple",
        }
    ]

    assert data["skus"][0]["id"] == str(sku.uuid)
    assert data["skus"][0]["price"] == 100000
    assert data["skus"][0]["discount"] == 10000
    assert data["skus"][0]["cost_price"] == 80000
    assert isinstance(data["skus"][0]["price"], int)


@pytest.mark.django_db
def test_product_list_item_serializer_returns_integer_min_price():
    seller = SellerFactory()
    category = CategoryFactory()

    product = Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone",
        slug="iphone-list",
        description="desc",
        status=ProductStatus.CREATED,
    )
    Sku.objects.create(
        product=product,
        name="iPhone 128GB",
        price=100000,
        discount=0,
        cost_price=80000,
        stock_quantity=10,
        active_quantity=8,
        reserved_quantity=2,
        article="iphone-list-128gb",
    )

    data = ProductListItemSerializer(product).data

    assert data["min_price"] == 100000
    assert isinstance(data["min_price"], int)
