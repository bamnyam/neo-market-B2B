import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import Product, ProductStatus
from app.skus.models import ReserveOperation, Sku
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.fixture
def client():
    client = APIClient()
    client.credentials(HTTP_X_SERVICE_KEY=settings.B2B_TO_B2C_KEY)

    return client


@pytest.fixture
def seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory()


@pytest.fixture
def product(
    seller,
    category,
):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug="iphone-15-reserve",
        description="desc",
        status=ProductStatus.MODERATED,
    )


def make_sku(
    product,
    *,
    article,
    active_quantity,
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


@pytest.mark.django_db
def test_reserve_all_skus_succeeds(
    client,
    product,
):
    first_sku = make_sku(
        product,
        article="iphone-15-black-reserve-happy",
        active_quantity=10,
    )
    second_sku = make_sku(
        product,
        article="iphone-15-white-reserve-happy",
        active_quantity=5,
    )

    response = client.post(
        "/api/v1/reserve",
        {
            "idempotency_key": str(uuid.uuid4()),
            "items": [
                {
                    "sku_id": str(first_sku.uuid),
                    "quantity": 2,
                },
                {
                    "sku_id": str(second_sku.uuid),
                    "quantity": 1,
                },
            ],
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data == {
        "reserved": True,
        "items": [
            {
                "sku_id": str(first_sku.uuid),
                "reserved_quantity": 2,
                "remaining_stock": 8,
            },
            {
                "sku_id": str(second_sku.uuid),
                "reserved_quantity": 1,
                "remaining_stock": 4,
            },
        ],
    }

    first_sku.refresh_from_db()
    second_sku.refresh_from_db()

    assert first_sku.active_quantity == 8
    assert first_sku.reserved_quantity == 2
    assert first_sku.active_quantity + first_sku.reserved_quantity == (
        first_sku.stock_quantity
    )

    assert second_sku.active_quantity == 4
    assert second_sku.reserved_quantity == 1
    assert second_sku.active_quantity + second_sku.reserved_quantity == (
        second_sku.stock_quantity
    )


@pytest.mark.django_db
def test_partial_insufficient_stock_returns_409_all_rollback(
    client,
    product,
):
    available_sku = make_sku(
        product,
        article="iphone-15-black-reserve-rollback",
        active_quantity=10,
    )
    insufficient_sku = make_sku(
        product,
        article="iphone-15-white-reserve-rollback",
        active_quantity=3,
    )

    response = client.post(
        "/api/v1/reserve",
        {
            "idempotency_key": str(uuid.uuid4()),
            "items": [
                {
                    "sku_id": str(available_sku.uuid),
                    "quantity": 2,
                },
                {
                    "sku_id": str(insufficient_sku.uuid),
                    "quantity": 5,
                },
            ],
        },
        format="json",
    )

    assert response.status_code == 409, response.data
    assert response.data == {
        "reserved": False,
        "failed_items": [
            {
                "sku_id": str(insufficient_sku.uuid),
                "requested": 5,
                "available": 3,
                "reason": "INSUFFICIENT_STOCK",
            }
        ],
    }

    available_sku.refresh_from_db()
    insufficient_sku.refresh_from_db()

    assert available_sku.active_quantity == 10
    assert available_sku.reserved_quantity == 0
    assert insufficient_sku.active_quantity == 3
    assert insufficient_sku.reserved_quantity == 0
    assert ReserveOperation.objects.count() == 0


@pytest.mark.django_db
def test_idempotent_reserve_returns_200_without_double_deduction(
    client,
    product,
):
    sku = make_sku(
        product,
        article="iphone-15-black-reserve-idempotent",
        active_quantity=4,
    )
    idempotency_key = str(uuid.uuid4())
    payload = {
        "idempotency_key": idempotency_key,
        "items": [
            {
                "sku_id": str(sku.uuid),
                "quantity": 2,
            }
        ],
    }

    first_response = client.post(
        "/api/v1/reserve",
        payload,
        format="json",
    )
    second_response = client.post(
        "/api/v1/reserve",
        payload,
        format="json",
    )

    assert first_response.status_code == 200, first_response.data
    assert second_response.status_code == 200, second_response.data
    assert second_response.data == first_response.data

    sku.refresh_from_db()

    assert sku.active_quantity == 2
    assert sku.reserved_quantity == 2
    assert ReserveOperation.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@patch("app.skus.integration.sku_events.requests.post")
def test_sku_out_of_stock_event_emitted(
    requests_post,
    client,
    product,
):
    sku = make_sku(
        product,
        article="iphone-15-black-reserve-out-of-stock",
        active_quantity=1,
    )

    response = client.post(
        "/api/v1/reserve",
        {
            "idempotency_key": str(uuid.uuid4()),
            "items": [
                {
                    "sku_id": str(sku.uuid),
                    "quantity": 1,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200, response.data

    requests_post.assert_called_once()

    call = requests_post.call_args

    assert call.args[0] == f"{settings.B2C_URL}/api/v1/events/product"
    assert call.kwargs["headers"] == {
        "X-Service-Key": settings.B2B_TO_B2C_KEY,
    }

    payload = call.kwargs["json"]

    assert payload["event"] == "SKU_OUT_OF_STOCK"
    assert payload["sku_id"] == str(sku.uuid)
    assert payload["product_id"] == str(product.uuid)
    assert payload["date"].endswith("Z")


@pytest.mark.django_db
def test_unreserve_restores_quantities(
    client,
    product,
):
    sku = make_sku(
        product,
        article="iphone-15-black-unreserve",
        active_quantity=8,
        reserved_quantity=2,
    )

    response = client.post(
        "/api/v1/unreserve",
        {
            "order_id": str(uuid.uuid4()),
            "items": [
                {
                    "sku_id": str(sku.uuid),
                    "quantity": 2,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data == {
        "ok": True,
    }

    sku.refresh_from_db()

    assert sku.active_quantity == 10
    assert sku.reserved_quantity == 0
    assert sku.active_quantity + sku.reserved_quantity == sku.stock_quantity
