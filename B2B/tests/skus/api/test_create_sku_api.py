import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from unittest.mock import patch

from app.products.models import Product, ProductStatus
from app.skus.models import Sku
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


@pytest.fixture
def product(seller, category):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug="iphone-15",
        description="desc",
        status=ProductStatus.CREATED,
    )


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_first_sku_transitions_product_to_on_moderation(
    requests_post,
    auth_client,
    product,
):
    response = auth_client.post(
        "/api/v1/skus",
        {
            "product_id": str(product.uuid),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [],
        },
        format="json",
    )

    assert response.status_code == 201, response.data

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION
    assert Sku.objects.count() == 1

    sku = Sku.objects.first()

    assert response.data["id"] == str(sku.uuid)
    assert response.data["product_id"] == str(product.uuid)
    assert response.data["name"] == "256GB Black"
    assert response.data["price"] == 12999000
    assert response.data["cost_price"] == 9500000
    assert response.data["discount"] == 0
    assert response.data["image"] == "/s3/iphone15-black-256.jpg"
    assert response.data["active_quantity"] == 0
    assert response.data["reserved_quantity"] == 0
    assert response.data["characteristics"] == []


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_first_sku_emits_created_event_to_moderation(
    requests_post,
    auth_client,
    product,
):
    response = auth_client.post(
        "/api/v1/skus",
        {
            "product_id": str(product.uuid),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [],
        },
        format="json",
    )

    assert response.status_code == 201, response.data

    requests_post.assert_called_once()

    call = requests_post.call_args

    assert call.args[0] == (f"{settings.MODERATION_URL}/api/v1/events/product")

    assert call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_MOD_KEY,
    }

    payload = call.kwargs["json"]

    assert payload["event"] == "CREATED"
    assert payload["product_id"] == str(product.uuid)
    assert payload["seller_id"] == str(product.seller.uuid)
    assert "idempotency_key" in payload
    assert "date" in payload


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_second_sku_no_state_change(
    requests_post,
    auth_client,
    product,
):
    product.status = ProductStatus.ON_MODERATION
    product.save(update_fields=["status"])

    existing_sku = Sku.objects.create(
        product=product,
        name="128GB Black",
        price=9999000,
        cost_price=7000000,
        discount=0,
        stock_quantity=0,
        active_quantity=0,
        reserved_quantity=0,
        article="iphone-15-128-black",
    )

    response = auth_client.post(
        "/api/v1/skus",
        {
            "product_id": str(product.uuid),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [],
        },
        format="json",
    )

    assert response.status_code == 201, response.data

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION
    assert Sku.objects.count() == 2
    assert Sku.objects.filter(id=existing_sku.id).exists()

    requests_post.assert_not_called()


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_add_sku_to_hard_blocked_returns_403(
    requests_post,
    auth_client,
    product,
):
    product.status = ProductStatus.HARD_BLOCKED
    product.save(update_fields=["status"])

    response = auth_client.post(
        "/api/v1/skus",
        {
            "product_id": str(product.uuid),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [],
        },
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "FORBIDDEN",
        "message": "Cannot add SKU to hard-blocked product",
    }

    product.refresh_from_db()

    assert product.status == ProductStatus.HARD_BLOCKED
    assert Sku.objects.count() == 0

    requests_post.assert_not_called()
