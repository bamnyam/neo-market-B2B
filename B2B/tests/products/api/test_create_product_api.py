import uuid

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import Product, ProductStatus
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


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
    category,
):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "description": "desc",
            "category_id": str(category.id),
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        },
        format="json",
    )

    print(response.status_code)
    print(response.data)

    assert response.status_code == 201
    assert response.data["status"] == ProductStatus.CREATED
    assert response.data["skus"] == []
    assert Product.objects.count() == 1


@pytest.mark.django_db
def test_missing_images_returns_400(auth_client, category):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "description": "desc",
            "category_id": str(category.id),
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "images"


@pytest.mark.django_db
def test_missing_category_returns_400(auth_client):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "description": "desc",
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"


@pytest.mark.django_db
def test_invalid_category_id_returns_400(auth_client):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "description": "desc",
            "category_id": "invalid-category-id",
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"


@pytest.mark.django_db
def test_not_existing_category_returns_400(auth_client):
    response = auth_client.post(
        "/api/v1/products",
        {
            "title": "iPhone",
            "description": "desc",
            "category_id": str(uuid.uuid4()),
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["field"] == "category_id"
    assert "Category not found" in response.data["message"]
