import uuid
from unittest.mock import patch

import jwt
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from app.products.models import Product, ProductFieldReport, ProductStatus
from app.skus.models import Sku
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def moderation_client(client):
    client.credentials(HTTP_X_SERVICE_KEY=settings.B2B_TO_MOD_KEY)
    return client


@pytest.fixture
def seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory()


@pytest.fixture
def seller_token(seller):
    return jwt.encode(
        {"seller_id": seller.id},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


@pytest.fixture
def seller_client(seller_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {seller_token}")
    return client


@pytest.fixture
def product(seller, category):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone",
        slug=f"iphone-{uuid.uuid4()}",
        description="desc",
        status=ProductStatus.ON_MODERATION,
        blocking_reason_id=uuid.uuid4(),
        blocking_reason_title="Old reason",
        moderator_comment="Old comment",
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
        article=f"iphone-128gb-{uuid.uuid4()}",
    )


def moderation_payload(product, **overrides):
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "product_id": str(product.uuid),
        "event_type": ProductStatus.MODERATED,
        "occurred_at": timezone.now().isoformat().replace("+00:00", "Z"),
    }
    payload.update(overrides)
    return payload


def full_contract_payload(product, **overrides):
    payload = moderation_payload(
        product,
        moderator_id=str(uuid.uuid4()),
        moderator_comment="string",
        blocking_reason_id=str(uuid.uuid4()),
        hard_block=False,
        field_reports=[
            {
                "field_name": "string",
                "sku_id": str(uuid.uuid4()),
                "comment": "string",
            }
        ],
    )
    payload.update(overrides)
    return payload


def blocked_payload(product, sku=None, **overrides):
    payload = moderation_payload(
        product,
        event_type=ProductStatus.BLOCKED,
        hard_block=False,
        blocking_reason_id=str(uuid.uuid4()),
        moderator_comment="Несоответствие описания и фотографий",
        field_reports=[
            {
                "field_name": "description",
                "sku_id": str(sku.uuid) if sku else None,
                "comment": "Текст описания скопирован с другого товара",
            }
        ],
    )
    payload.update(overrides)
    return payload


def build_expected_idempotency_key(product_id, event_type):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{product_id}:{event_type}"))


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_full_contract_moderated_payload_is_accepted(
    requests_post,
    moderation_client,
    product,
):
    response = moderation_client.post(
        "/api/v1/moderation/events",
        full_contract_payload(product),
        format="json",
    )

    assert response.status_code == 204

    product.refresh_from_db()

    assert product.status == ProductStatus.MODERATED
    assert product.blocking_reason_id is None
    assert product.field_reports.count() == 0
    requests_post.assert_not_called()


@pytest.mark.django_db
def test_status_alias_is_not_part_of_contract(moderation_client, product):
    response = moderation_client.post(
        "/api/v1/moderation/events",
        moderation_payload(product, status=ProductStatus.MODERATED),
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_moderated_event_clears_blocking_data(
    requests_post,
    moderation_client,
    product,
):
    ProductFieldReport.objects.create(
        product=product,
        field_name="description",
        comment="Old report",
    )

    response = moderation_client.post(
        "/api/v1/moderation/events",
        moderation_payload(product),
        format="json",
    )

    assert response.status_code == 204

    product.refresh_from_db()

    assert product.status == ProductStatus.MODERATED
    assert product.blocking_reason_id is None
    assert product.blocking_reason_title is None
    assert product.moderator_comment is None
    assert product.field_reports.count() == 0
    requests_post.assert_not_called()


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_blocked_soft_saves_field_reports(
    requests_post,
    moderation_client,
    product,
    sku,
):
    payload = blocked_payload(product, sku)

    response = moderation_client.post(
        "/api/v1/moderation/events",
        payload,
        format="json",
    )

    assert response.status_code == 204

    product.refresh_from_db()
    report = product.field_reports.get()

    assert product.status == ProductStatus.BLOCKED
    assert str(product.blocking_reason_id) == payload["blocking_reason_id"]
    assert product.blocking_reason_title == ""
    assert product.moderator_comment == payload["moderator_comment"]
    assert report.field_name == "description"
    assert report.sku == sku
    assert report.comment == payload["field_reports"][0]["comment"]

    requests_post.assert_called_once()
    call = requests_post.call_args

    assert call.args[0] == f"{settings.B2C_URL}/api/v1/events/product"
    assert call.kwargs["headers"] == {"X-Service-Key": settings.B2B_TO_B2C_KEY}

    b2c_payload = call.kwargs["json"]

    assert b2c_payload["idempotency_key"] == build_expected_idempotency_key(
        product.uuid,
        "PRODUCT_BLOCKED",
    )
    assert b2c_payload["event"] == "PRODUCT_BLOCKED"
    assert b2c_payload["product_id"] == str(product.uuid)
    assert b2c_payload["sku_ids"] == [str(sku.uuid)]
    assert b2c_payload["date"].endswith("Z")


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_blocked_hard_sets_terminal_status(
    requests_post,
    moderation_client,
    product,
    sku,
):
    payload = blocked_payload(product, sku, hard_block=True)

    response = moderation_client.post(
        "/api/v1/moderation/events",
        payload,
        format="json",
    )

    assert response.status_code == 204

    product.refresh_from_db()

    assert product.status == ProductStatus.HARD_BLOCKED
    assert str(product.blocking_reason_id) == payload["blocking_reason_id"]
    requests_post.assert_called_once()
    assert requests_post.call_args.kwargs["json"]["event"] == "PRODUCT_BLOCKED"


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_hard_blocked_product_rejects_seller_edits(
    requests_post,
    moderation_client,
    seller_client,
    product,
):
    response = moderation_client.post(
        "/api/v1/moderation/events",
        blocked_payload(product, hard_block=True),
        format="json",
    )

    assert response.status_code == 204

    put_response = seller_client.put(
        f"/api/v1/products/{product.uuid}",
        {
            "title": "New title",
        },
        format="json",
    )
    delete_response = seller_client.delete(
        f"/api/v1/products/{product.uuid}",
        format="json",
    )

    product.refresh_from_db()

    assert put_response.status_code == 403
    assert delete_response.status_code == 403
    assert product.deleted is False


@pytest.mark.django_db
@patch("app.products.integration.b2c_events.requests.post")
def test_duplicate_event_same_idempotency_key_no_side_effects(
    requests_post,
    moderation_client,
    product,
    sku,
):
    idempotency_key = str(uuid.uuid4())

    first_response = moderation_client.post(
        "/api/v1/moderation/events",
        blocked_payload(product, idempotency_key=idempotency_key),
        format="json",
    )
    second_response = moderation_client.post(
        "/api/v1/moderation/events",
        moderation_payload(product, idempotency_key=idempotency_key),
        format="json",
    )

    assert first_response.status_code == 204
    assert second_response.status_code == 204

    product.refresh_from_db()

    assert product.status == ProductStatus.BLOCKED
    assert product.blocking_reason_id is not None
    assert product.field_reports.count() == 1
    requests_post.assert_called_once()


@pytest.mark.django_db
def test_missing_service_key_returns_401(client, product):
    response = client.post(
        "/api/v1/moderation/events",
        moderation_payload(product),
        format="json",
    )

    assert response.status_code == 401
