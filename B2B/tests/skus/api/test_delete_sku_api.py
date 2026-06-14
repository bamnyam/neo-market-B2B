import uuid
from unittest.mock import patch

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

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


def make_product(
    seller,
    category,
    *,
    status=ProductStatus.CREATED,
    slug="iphone-15-delete-sku",
):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug=slug,
        description="desc",
        status=status,
    )


def make_sku(
    product,
    *,
    article,
    active_quantity=0,
    reserved_quantity=0,
):
    return Sku.objects.create(
        product=product,
        name=article,
        price=12999000,
        cost_price=9500000,
        discount=0,
        stock_quantity=active_quantity + reserved_quantity,
        active_quantity=active_quantity,
        reserved_quantity=reserved_quantity,
        article=article,
    )


def build_expected_idempotency_key(
    product_id,
    event_type,
):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{product_id}:{event_type}"))


@pytest.mark.django_db
def test_delete_sku_succeeds(
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller,
        category,
        status=ProductStatus.CREATED,
    )
    sku = make_sku(
        product,
        article="iphone-15-delete-sku-happy",
    )

    response = auth_client.delete(
        f"/api/v1/skus/{sku.uuid}",
        format="json",
    )

    assert response.status_code == 204
    assert response.content == b""
    assert not Sku.objects.filter(id=sku.id).exists()


@pytest.mark.django_db
def test_delete_sku_with_active_reserves_returns_409(
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller,
        category,
        status=ProductStatus.MODERATED,
        slug="iphone-15-delete-sku-reserved",
    )
    sku = make_sku(
        product,
        article="iphone-15-delete-sku-reserved",
        reserved_quantity=1,
    )

    response = auth_client.delete(
        f"/api/v1/skus/{sku.uuid}",
        format="json",
    )

    assert response.status_code == 409
    assert response.data == {
        "code": "CONFLICT",
        "message": "Cannot delete SKU with active reserves",
    }
    assert Sku.objects.filter(id=sku.id).exists()


@pytest.mark.django_db
@patch("app.skus.integration.moderation_events.requests.post")
def test_last_sku_on_moderation_transitions_product_to_created(
    requests_post,
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller,
        category,
        status=ProductStatus.ON_MODERATION,
        slug="iphone-15-delete-sku-last",
    )
    sku = make_sku(
        product,
        article="iphone-15-delete-sku-last",
    )

    response = auth_client.delete(
        f"/api/v1/skus/{sku.uuid}",
        format="json",
    )

    assert response.status_code == 204
    assert not Sku.objects.filter(id=sku.id).exists()

    product.refresh_from_db()

    assert product.status == ProductStatus.CREATED

    requests_post.assert_called_once()

    call = requests_post.call_args

    assert call.args[0] == f"{settings.MODERATION_URL}/api/v1/events/product"
    assert call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_MOD_KEY,
    }

    payload = call.kwargs["json"]

    assert payload == {
        "idempotency_key": build_expected_idempotency_key(
            product.uuid,
            "DELETED",
        ),
        "product_id": str(product.uuid),
        "seller_id": str(product.seller.uuid),
        "event": "DELETED",
        "date": payload["date"],
    }
    assert payload["date"].endswith("Z")


@pytest.mark.django_db
def test_delete_sku_hard_blocked_product_returns_403(
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller,
        category,
        status=ProductStatus.HARD_BLOCKED,
        slug="iphone-15-delete-sku-hard-blocked",
    )
    sku = make_sku(
        product,
        article="iphone-15-delete-sku-hard-blocked",
        reserved_quantity=1,
    )

    response = auth_client.delete(
        f"/api/v1/skus/{sku.uuid}",
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "FORBIDDEN",
        "message": "Cannot delete SKU of hard-blocked product",
    }
    assert Sku.objects.filter(id=sku.id).exists()


@pytest.mark.django_db
@patch("app.skus.integration.sku_events.requests.post")
def test_sku_out_of_stock_event_on_moderated_product(
    requests_post,
    auth_client,
    seller,
    category,
):
    product = make_product(
        seller,
        category,
        status=ProductStatus.MODERATED,
        slug="iphone-15-delete-sku-out-of-stock",
    )
    sku = make_sku(
        product,
        article="iphone-15-delete-sku-out-of-stock",
        active_quantity=3,
    )

    response = auth_client.delete(
        f"/api/v1/skus/{sku.uuid}",
        format="json",
    )

    assert response.status_code == 204
    assert not Sku.objects.filter(id=sku.id).exists()

    requests_post.assert_called_once()

    call = requests_post.call_args

    assert call.args[0] == f"{settings.B2C_URL}/api/v1/b2b/events"
    assert call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_B2C_KEY,
    }

    payload = call.kwargs["json"]

    assert payload["event_type"] == "SKU_OUT_OF_STOCK"
    assert payload["idempotency_key"] == build_expected_idempotency_key(
        sku.uuid,
        "SKU_OUT_OF_STOCK",
    )
    assert payload["occurred_at"].endswith("Z")
    assert payload["payload"] == {
        "product_id": str(product.uuid),
        "sku_id": str(sku.uuid),
        "available_quantity": 0,
    }
