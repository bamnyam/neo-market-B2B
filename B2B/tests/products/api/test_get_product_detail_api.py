import uuid

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import (
    Product,
    ProductCharacteristics,
    ProductFieldReport,
    ProductImages,
    ProductStatus,
)
from app.skus.models import (
    Sku,
    SkuCharacteristics,
    SkuImages,
)
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def seller():
    return SellerFactory()


@pytest.fixture
def other_seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory(name="iOS")


@pytest.fixture
def token(seller):
    return jwt.encode(
        {"seller_id": seller.id},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


@pytest.fixture
def auth_client(client, token):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_product(
    *,
    seller,
    category,
    status,
    slug,
):
    product = Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15 Pro Max",
        slug=slug,
        description="Флагманский смартфон Apple 2024 года",
        status=status,
        deleted=False,
    )
    product_image = ProductImages.objects.create(
        product=product,
        url="/s3/iphone15-front.jpg",
        ordering=0,
    )
    product_characteristic = ProductCharacteristics.objects.create(
        product=product,
        name="Бренд",
        value="Apple",
    )
    sku = Sku.objects.create(
        product=product,
        name="256GB Black",
        price=12999000,
        cost_price=9500000,
        discount=0,
        active_quantity=10,
        reserved_quantity=2,
        article=f"{slug}-256-black",
    )
    sku_image = SkuImages.objects.create(
        sku=sku,
        url="/s3/iphone15-black-256.jpg",
        ordering=0,
    )
    sku_characteristic = SkuCharacteristics.objects.create(
        sku=sku,
        name="Цвет",
        value="Чёрный",
    )
    return (
        product,
        sku,
        product_image,
        product_characteristic,
        sku_image,
        sku_characteristic,
    )


@pytest.mark.django_db
def test_get_moderated_product_returns_full_payload(
    auth_client,
    seller,
    category,
):
    (
        product,
        sku,
        product_image,
        product_characteristic,
        sku_image,
        sku_characteristic,
    ) = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.MODERATED,
        slug="iphone-15-pro-max",
    )

    response = auth_client.get(f"/api/v1/products/{product.uuid}")

    assert response.status_code == 200, response.data
    assert response.data["id"] == str(product.uuid)
    assert response.data["seller_id"] == str(seller.uuid)
    assert response.data["category_id"] == str(category.uuid)
    assert response.data["title"] == "iPhone 15 Pro Max"
    assert response.data["slug"] == "iphone-15-pro-max"
    assert response.data["description"] == "Флагманский смартфон Apple 2024 года"
    assert response.data["status"] == ProductStatus.MODERATED
    assert response.data["deleted"] is False
    assert response.data["blocked"] is False
    assert response.data["images"] == [
        {
            "id": str(product_image.uuid),
            "url": "/s3/iphone15-front.jpg",
            "ordering": 0,
        }
    ]
    assert response.data["characteristics"] == [
        {
            "id": str(product_characteristic.uuid),
            "name": "Бренд",
            "value": "Apple",
        }
    ]
    assert response.data["skus"] == [
        {
            "id": str(sku.uuid),
            "product_id": str(product.uuid),
            "name": "256GB Black",
            "price": 12999000,
            "discount": 0,
            "cost_price": 9500000,
            "stock_quantity": 0,
            "active_quantity": 10,
            "reserved_quantity": 2,
            "article": "iphone-15-pro-max-256-black",
            "images": [
                {
                    "id": str(sku_image.uuid),
                    "url": "/s3/iphone15-black-256.jpg",
                    "ordering": 0,
                }
            ],
            "characteristics": [
                {
                    "id": str(sku_characteristic.uuid),
                    "name": "Цвет",
                    "value": "Чёрный",
                }
            ],
            "created_at": response.data["skus"][0]["created_at"],
            "updated_at": response.data["skus"][0]["updated_at"],
        }
    ]
    assert response.data["created_at"] is not None
    assert response.data["updated_at"] is not None
    assert response.data["skus"][0]["created_at"] is not None
    assert response.data["skus"][0]["updated_at"] is not None
    assert response.data["blocking_reason"] is None
    assert response.data["field_reports"] == []


@pytest.mark.django_db
def test_get_blocked_product_returns_blocking_reason_and_field_reports(
    auth_client,
    seller,
    category,
):
    product, sku, *_ = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.BLOCKED,
        slug="blocked-iphone-15-pro-max",
    )
    blocking_reason_id = uuid.uuid4()
    product.blocking_reason_id = blocking_reason_id
    product.blocking_reason_title = "Описание не соответствует товару"
    product.moderator_comment = "Несоответствие описания и фотографий"
    product.save(
        update_fields=[
            "blocking_reason_id",
            "blocking_reason_title",
            "moderator_comment",
        ]
    )
    ProductFieldReport.objects.create(
        product=product,
        field_name=ProductFieldReport.FieldName.DESCRIPTION,
        comment="В описании указан неверный материал",
    )
    ProductFieldReport.objects.create(
        product=product,
        sku=sku,
        field_name=ProductFieldReport.FieldName.SKU_IMAGE,
        comment="Фото SKU не соответствует указанному цвету",
    )

    response = auth_client.get(f"/api/v1/products/{product.uuid}")

    assert response.status_code == 200, response.data
    assert response.data["blocked"] is True
    assert response.data["blocking_reason"] == {
        "id": str(blocking_reason_id),
        "title": "Описание не соответствует товару",
        "comment": "Несоответствие описания и фотографий",
    }
    assert response.data["field_reports"] == [
        {
            "field_name": "description",
            "sku_id": None,
            "comment": "В описании указан неверный материал",
        },
        {
            "field_name": "sku_image",
            "sku_id": str(sku.uuid),
            "comment": "Фото SKU не соответствует указанному цвету",
        },
    ]


@pytest.mark.django_db
def test_get_others_product_returns_404(
    auth_client,
    other_seller,
    category,
):
    product, *_ = make_product(
        seller=other_seller,
        category=category,
        status=ProductStatus.MODERATED,
        slug="other-seller-iphone",
    )

    response = auth_client.get(f"/api/v1/products/{product.uuid}")

    assert response.status_code == 404
    assert response.data == {
        "code": "NOT_FOUND",
        "message": "Product not found",
    }


@pytest.mark.django_db
def test_get_nonexistent_returns_404(auth_client):
    response = auth_client.get(f"/api/v1/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.data == {
        "code": "NOT_FOUND",
        "message": "Product not found",
    }


@pytest.mark.django_db
def test_get_invalid_uuid_returns_400(auth_client):
    response = auth_client.get("/api/v1/products/not-a-uuid")

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "id must be a valid UUID",
    }


@pytest.mark.django_db
def test_moderation_service_can_get_any_seller_product(
    client,
    other_seller,
    category,
):
    product, *_ = make_product(
        seller=other_seller,
        category=category,
        status=ProductStatus.MODERATED,
        slug="moderation-service-iphone",
    )
    client.credentials(HTTP_X_SERVICE_KEY=settings.B2B_TO_MOD_KEY)

    response = client.get(f"/api/v1/products/{product.uuid}")

    assert response.status_code == 200, response.data
    assert response.data["id"] == str(product.uuid)
