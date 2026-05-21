import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from unittest.mock import patch

from app.products.models import Product
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
        title="iPhone",
        slug="iphone",
        description="desc",
    )


@pytest.fixture
def sku(product):
    return Sku.objects.create(
        product=product,
        name="iPhone 128GB",
        price=100000,
        discount=0,
        cost_price=80000,
        stock_quantity=10,
        active_quantity=10,
        reserved_quantity=0,
        article="iphone-128gb",
    )


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_sets_deleted_true(
    requests_post,
    auth_client,
    product,
):
    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {"ok": True}

    product.refresh_from_db()

    assert product.deleted is True
    assert requests_post.call_count == 2


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_emits_event_to_moderation(
    requests_post,
    auth_client,
    product,
):
    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 200

    assert requests_post.call_count == 2

    moderation_call = requests_post.call_args_list[0]

    assert moderation_call.args[0] == (
        f"{settings.MODERATION_URL}/api/v1/events/product"
    )

    assert moderation_call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_MOD_KEY,
    }

    payload = moderation_call.kwargs["json"]

    assert payload["event"] == "DELETED"
    assert payload["product_id"] == str(product.uuid)
    assert payload["seller_id"] == str(product.seller.uuid)
    assert "idempotency_key" in payload
    assert "date" in payload


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_emits_product_deleted_to_b2c(
    requests_post,
    auth_client,
    product,
    sku,
):
    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 200

    assert requests_post.call_count == 2

    b2c_call = requests_post.call_args_list[1]

    assert b2c_call.args[0] == (f"{settings.B2C_URL}/api/v1/events/product")

    assert b2c_call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_B2C_KEY,
    }

    payload = b2c_call.kwargs["json"]

    assert payload["event"] == "PRODUCT_DELETED"
    assert payload["product_id"] == str(product.uuid)
    assert payload["sku_ids"] == [str(sku.uuid)]
    assert "idempotency_key" in payload
    assert "date" in payload


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_already_deleted_returns_400(
    requests_post,
    auth_client,
    product,
):
    product.deleted = True
    product.save(update_fields=["deleted"])

    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "Product already deleted",
    }

    product.refresh_from_db()

    assert product.deleted is True
    requests_post.assert_not_called()


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_others_product_returns_403(
    requests_post,
    auth_client,
    other_seller,
    category,
):
    product = Product.objects.create(
        seller=other_seller,
        category=category,
        title="Other iPhone",
        slug="other-iphone",
        description="desc",
    )

    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "NOT_OWNER",
        "message": "Product does not belong to the authenticated seller",
    }

    product.refresh_from_db()

    assert product.deleted is False
    requests_post.assert_not_called()


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_not_found_returns_404(
    requests_post,
    auth_client,
):
    response = auth_client.delete(
        "/api/v1/products/00000000-0000-0000-0000-000000000000",
        format="json",
    )

    assert response.status_code == 404
    assert response.data == {
        "code": "NOT_FOUND",
        "message": "Product not found",
    }

    requests_post.assert_not_called()

@pytest.mark.django_db
def test_deleted_product_not_in_seller_list(
    auth_client,
    seller,
    category,
):
    active_product = Product.objects.create(
        seller=seller,
        category=category,
        title="Active iPhone",
        slug="active-iphone",
        description="desc",
        deleted=False,
    )

    deleted_product = Product.objects.create(
        seller=seller,
        category=category,
        title="Deleted iPhone",
        slug="deleted-iphone",
        description="desc",
        deleted=True,
    )

    response = auth_client.get(
        "/api/v1/products",
        format="json",
    )

    assert response.status_code == 200

    product_ids = [
        item["id"]
        for item in response.data
    ]

    assert str(active_product.uuid) in product_ids
    assert str(deleted_product.uuid) not in product_ids