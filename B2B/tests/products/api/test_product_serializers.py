import uuid

import pytest

from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductResponseSerializer,
)
from app.products.models import (
    Product,
    ProductCharacteristics,
    ProductImages,
    ProductStatus,
)
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.mark.django_db
def test_product_create_serializer_creates_product_with_images_and_characteristics():
    seller = SellerFactory()
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "description": "desc",
            "category_id": str(category.id),
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
            "characteristics": [{"name": "brand", "value": "Apple"}],
        },
        context={"seller": seller},
    )

    assert serializer.is_valid(), serializer.errors

    product = serializer.save()

    assert product.seller_id == seller.id
    assert product.category_id == category.id
    assert product.status == ProductStatus.CREATED
    assert Product.objects.count() == 1
    assert ProductImages.objects.count() == 1
    assert ProductCharacteristics.objects.count() == 1


@pytest.mark.django_db
def test_product_create_serializer_rejects_empty_images():
    category = CategoryFactory()

    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "description": "desc",
            "category_id": str(category.id),
            "images": [],
        },
    )

    assert not serializer.is_valid()
    assert "images" in serializer.errors


@pytest.mark.django_db
def test_product_create_serializer_rejects_missing_category():
    serializer = ProductCreateSerializer(
        data={
            "title": "iPhone",
            "description": "desc",
            "category_id": str(uuid.uuid4()),
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        },
    )

    assert not serializer.is_valid()
    assert "category_id" in serializer.errors


@pytest.mark.django_db
def test_product_response_serializer_returns_expected_payload():
    seller = SellerFactory()
    category = CategoryFactory()
    product = Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone",
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

    data = ProductResponseSerializer(product).data

    assert data["id"] == product.id
    assert data["seller_id"] == str(seller.id)
    assert data["category_id"] == str(category.id)
    assert data["title"] == "iPhone"
    assert data["description"] == "desc"
    assert data["status"] == ProductStatus.CREATED
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
    assert data["images"] == [
        {
            "id": str(image.id),
            "url": "/s3/image.jpg",
            "ordering": 0,
        }
    ]

    assert data["characteristics"] == [
        {
            "id": str(characteristic.id),
            "name": "brand",
            "value": "Apple",
        }
    ]
    assert data["skus"] == []
