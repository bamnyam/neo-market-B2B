import uuid
from unittest.mock import patch

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import (
    Product,
    ProductImages,
    ProductStatus,
)
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
def other_seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory()


@pytest.fixture
def other_category():
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


def build_expected_idempotency_key(
    product_id,
    event_type,
):
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{str(product_id)}:{event_type}",
        )
    )


def make_product(
    *,
    seller,
    category,
    status,
    slug="iphone-15",
):
    product = Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug=slug,
        description="desc",
        status=status,
    )
    ProductImages.objects.create(
        product=product,
        url="/s3/old.jpg",
        ordering=0,
    )
    return product


def product_payload(category):
    return {
        "title": "iPhone 15 Pro Max updated",
        "slug": "iphone-15-pro-max-updated",
        "description": "updated desc",
        "category_id": str(category.uuid),
        "images": [
            {
                "url": "/s3/new.jpg",
                "ordering": 0,
            }
        ],
        "characteristics": [
            {
                "name": "brand",
                "value": "Apple",
            }
        ],
    }


def assert_edited_event(
    *,
    requests_post,
    product,
):
    requests_post.assert_called_once()
    call = requests_post.call_args

    assert call.args[0] == f"{settings.MODERATION_URL}/api/v1/events/product"
    assert call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_MOD_KEY,
    }

    payload = call.kwargs["json"]

    assert payload["event"] == "EDITED"
    assert payload["product_id"] == str(product.uuid)
    assert payload["seller_id"] == str(product.seller.uuid)
    assert payload["idempotency_key"] == build_expected_idempotency_key(
        product.uuid,
        "EDITED",
    )
    assert payload["date"].endswith("Z")


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_edit_moderated_product_returns_to_on_moderation(
    requests_post,
    auth_client,
    seller,
    category,
    other_category,
):
    product = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.MODERATED,
    )

    response = auth_client.put(
        f"/api/v1/products/{product.uuid}",
        product_payload(other_category),
        format="json",
    )

    assert response.status_code == 200, response.data

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION
    assert product.title == "iPhone 15 Pro Max updated"
    assert product.category == other_category
    assert response.data["status"] == ProductStatus.ON_MODERATION
    assert response.data["images"][0]["url"] == "/s3/new.jpg"

    assert_edited_event(
        requests_post=requests_post,
        product=product,
    )


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_edit_blocked_product_returns_to_on_moderation(
    requests_post,
    auth_client,
    seller,
    category,
    other_category,
):
    product = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.BLOCKED,
    )

    response = auth_client.put(
        f"/api/v1/products/{product.uuid}",
        product_payload(other_category),
        format="json",
    )

    assert response.status_code == 200, response.data

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION
    assert response.data["status"] == ProductStatus.ON_MODERATION

    assert_edited_event(
        requests_post=requests_post,
        product=product,
    )


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_reserves_preserved_after_sku_edit(
    requests_post,
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.MODERATED,
    )
    sku = Sku.objects.create(
        product=product,
        name="256GB Black",
        price=12999000,
        cost_price=9500000,
        discount=0,
        stock_quantity=10,
        active_quantity=7,
        reserved_quantity=3,
        article="iphone-15-256-black",
    )

    response = auth_client.put(
        f"/api/v1/skus/{sku.uuid}",
        {
            "name": "256GB Black Titanium",
            "price": 13499000,
            "cost_price": 9800000,
            "discount": 500000,
            "article": "iphone-15-256-black-titanium",
            "image": "/s3/iphone15-black-titanium.jpg",
            "characteristics": [
                {
                    "name": "color",
                    "value": "black titanium",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200, response.data

    sku.refresh_from_db()
    product.refresh_from_db()

    assert sku.name == "256GB Black Titanium"
    assert int(sku.price) == 13499000
    assert sku.stock_quantity == 10
    assert sku.active_quantity == 7
    assert sku.reserved_quantity == 3
    assert response.data["reserved_quantity"] == 3
    assert product.status == ProductStatus.ON_MODERATION

    assert_edited_event(
        requests_post=requests_post,
        product=product,
    )


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_edit_hard_blocked_returns_403(
    requests_post,
    auth_client,
    seller,
    category,
    other_category,
):
    product = make_product(
        seller=seller,
        category=category,
        status=ProductStatus.HARD_BLOCKED,
    )

    response = auth_client.put(
        f"/api/v1/products/{product.uuid}",
        product_payload(other_category),
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "FORBIDDEN",
        "message": "Cannot edit hard-blocked product",
    }

    product.refresh_from_db()

    assert product.status == ProductStatus.HARD_BLOCKED
    requests_post.assert_not_called()


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_edit_others_product_returns_403(
    requests_post,
    auth_client,
    other_seller,
    category,
    other_category,
):
    product = make_product(
        seller=other_seller,
        category=category,
        status=ProductStatus.MODERATED,
        slug="other-iphone-15",
    )

    response = auth_client.put(
        f"/api/v1/products/{product.uuid}",
        product_payload(other_category),
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "NOT_OWNER",
        "message": "Product does not belong to the authenticated seller",
    }

    product.refresh_from_db()

    assert product.status == ProductStatus.MODERATED
    requests_post.assert_not_called()
