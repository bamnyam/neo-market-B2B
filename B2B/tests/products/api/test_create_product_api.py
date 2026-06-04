import uuid

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import (
    Product,
    ProductStatus,
)
from tests.factories.category_factory import (
    CategoryFactory,
)
from tests.factories.seller_factory import (
    SellerFactory,
)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory()


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


@pytest.mark.django_db
def test_create_product_returns_201_with_created_status(
    auth_client,
    seller,
    category,
):
    response = auth_client.post(
        "/api/v1/products",
        {
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
        format="json",
    )

    assert response.status_code == 201, response.data

    assert response.data["id"] is not None
    assert response.data["seller_id"] == str(seller.uuid)
    assert response.data["category_id"] == str(category.uuid)
    assert response.data["title"] == "iPhone"
    assert response.data["slug"] == "iphone"
    assert response.data["description"] == "desc"
    assert response.data["status"] == ProductStatus.CREATED
    assert response.data["deleted"] is False
    assert response.data["blocking_reason_id"] is None
    assert response.data["moderator_comment"] is None

    assert response.data["images"] == [
        {
            "id": response.data["images"][0]["id"],
            "url": "/s3/image.jpg",
            "ordering": 0,
        }
    ]

    assert response.data["characteristics"] == [
        {
            "id": response.data["characteristics"][0]["id"],
            "name": "brand",
            "value": "Apple",
        }
    ]

    assert response.data["skus"] == []
    assert response.data["created_at"] is not None
    assert response.data["updated_at"] is not None

    assert Product.objects.count() == 1

    product = Product.objects.first()

    assert response.data["id"] == str(product.uuid)
    assert product.seller == seller
    assert product.category == category
    assert product.slug == "iphone"


@pytest.mark.django_db
def test_create_product_generates_slug_when_missing(
    auth_client,
    category,
):
    response = auth_client.post(
        "/api/v1/products",
        {
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
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["slug"] == "iphone-15"


@pytest.mark.django_db
def test_create_product_without_images_returns_400(
    auth_client,
    category,
):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "slug": "iphone-no-images",
            "description": "desc",
            "category_id": str(category.uuid),
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "images"

    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_missing_category_returns_400(
    auth_client,
):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "slug": "iphone",
            "description": "desc",
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"


@pytest.mark.django_db
def test_invalid_category_id_returns_400(
    auth_client,
):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "slug": "iphone",
            "description": "desc",
            "category_id": "invalid-category-id",
            "images": [
                {
                    "url": "/s3/image.jpg",
                    "ordering": 0,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"


@pytest.mark.django_db
def test_not_existing_category_returns_400(
    auth_client,
):
    response = auth_client.post(
        "/api/v1/products",
        {
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
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"
    assert "Category not found" in response.data["message"]


@pytest.mark.django_db
def test_duplicate_slug_returns_400(
    auth_client,
    seller,
    category,
):
    Product.objects.create(
        seller=seller,
        category=category,
        title="Old product",
        slug="iphone",
        description="desc",
    )

    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "New iPhone",
            "slug": "iphone",
            "description": "desc",
            "category_id": str(category.uuid),
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "slug"


@pytest.mark.django_db
def test_duplicate_image_ordering_returns_400(
    auth_client,
    category,
):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "slug": "iphone-duplicate-ordering",
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
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "images"
