import uuid
from unittest.mock import patch

import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

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


def build_expected_idempotency_key(
    product_id,
    event_type,
):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{product_id}:{event_type}"))


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

    assert response.status_code == 204
    assert response.content == b""

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

    assert response.status_code == 204

    assert requests_post.call_count == 2

    moderation_call = requests_post.call_args_list[0]

    assert moderation_call.args[0] == (
        f"{settings.MODERATION_URL}/api/v1/events/product"
    )

    assert moderation_call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_MOD_KEY,
    }

    payload = moderation_call.kwargs["json"]

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

    assert response.status_code == 204

    assert requests_post.call_count == 2

    b2c_call = requests_post.call_args_list[1]

    assert b2c_call.args[0] == (f"{settings.B2C_URL}/api/v1/events/product")

    assert b2c_call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_B2C_KEY,
    }

    payload = b2c_call.kwargs["json"]

    assert payload == {
        "idempotency_key": build_expected_idempotency_key(
            product.uuid,
            "DELETED",
        ),
        "event": "PRODUCT_DELETED",
        "product_id": str(product.uuid),
        "sku_ids": [str(sku.uuid)],
        "date": payload["date"],
    }

    assert payload["date"].endswith("Z")


@pytest.mark.django_db
@patch("app.products.integration.product_events.requests.post")
def test_delete_generates_stable_idempotency_keys(
    requests_post,
    auth_client,
    product,
):
    response = auth_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    assert response.status_code == 204

    moderation_payload = requests_post.call_args_list[0].kwargs["json"]
    b2c_payload = requests_post.call_args_list[1].kwargs["json"]

    assert moderation_payload["idempotency_key"] == (
        build_expected_idempotency_key(
            product.uuid,
            "DELETED",
        )
    )

    assert b2c_payload["idempotency_key"] == (
        build_expected_idempotency_key(
            product.uuid,
            "DELETED",
        )
    )


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
        "message": ("Product does not belong to the authenticated seller"),
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

    product_ids = [item["id"] for item in response.data["items"]]

    assert str(active_product.uuid) in product_ids
    assert str(deleted_product.uuid) not in product_ids

    assert response.data["total_count"] == 1
    assert response.data["limit"] == 20
    assert response.data["offset"] == 0


@pytest.mark.django_db
def test_seller_list_filters_by_search(
    auth_client,
    seller,
    category,
):
    matched_product = Product.objects.create(
        seller=seller,
        category=category,
        title="Searchable iPhone",
        slug="searchable-iphone",
        description="desc",
        deleted=False,
    )
    unmatched_product = Product.objects.create(
        seller=seller,
        category=category,
        title="Pixel",
        slug="pixel",
        description="desc",
        deleted=False,
    )

    response = auth_client.get(
        "/api/v1/products",
        {"search": "iphone"},
        format="json",
    )

    assert response.status_code == 200, response.data

    product_ids = [item["id"] for item in response.data["items"]]

    assert product_ids == [str(matched_product.uuid)]
    assert str(unmatched_product.uuid) not in product_ids
    assert response.data["total_count"] == 1


@pytest.mark.django_db
def test_seller_list_invalid_status_returns_400(auth_client):
    response = auth_client.get(
        "/api/v1/products",
        {"status": "INVALID"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "status must be a valid ProductStatus",
        "field": "status",
    }


@pytest.mark.django_db
def test_seller_list_invalid_limit_returns_400(auth_client):
    response = auth_client.get(
        "/api/v1/products",
        {"limit": "0"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "limit must be between 1 and 100",
        "field": "limit",
    }


@pytest.mark.django_db
def test_seller_list_owner_query_param_returns_400(auth_client):
    response = auth_client.get(
        "/api/v1/products",
        {"seller_id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "seller_id is not allowed",
        "field": "seller_id",
    }
