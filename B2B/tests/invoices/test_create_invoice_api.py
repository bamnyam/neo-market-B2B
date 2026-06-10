import jwt
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.invoices.models import Invoice, InvoiceItem, InvoiceStatus
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


def create_product(seller, category, status=ProductStatus.MODERATED, slug="iphone"):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug=slug,
        description="desc",
        status=status,
    )


def create_sku(product, article="iphone-15-256-black"):
    return Sku.objects.create(
        product=product,
        name="256GB Black",
        price=12999000,
        cost_price=9500000,
        discount=0,
        stock_quantity=0,
        active_quantity=0,
        reserved_quantity=0,
        article=article,
    )


@pytest.mark.django_db
def test_create_invoice_with_moderated_sku_returns_201(
    auth_client,
    seller,
    category,
):
    product = create_product(seller, category)
    sku = create_sku(product)

    response = auth_client.post(
        "/api/v1/invoices",
        {
            "items": [
                {
                    "sku_id": str(sku.uuid),
                    "quantity": 10,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["id"] is not None
    assert response.data["seller_id"] == str(seller.uuid)
    assert response.data["status"] == InvoiceStatus.CREATED
    assert response.data["created_at"] is not None
    assert response.data["updated_at"] is not None
    assert response.data["accepted_at"] is None
    assert response.data["items"] == [
        {
            "id": response.data["items"][0]["id"],
            "sku_id": str(sku.uuid),
            "quantity": 10,
            "accepted_quantity": 0,
        }
    ]

    invoice = Invoice.objects.get(uuid=response.data["id"])
    item = InvoiceItem.objects.get(invoice=invoice)

    assert invoice.seller == seller
    assert invoice.status == InvoiceStatus.CREATED
    assert item.sku == sku
    assert item.quantity == 10
    assert item.accepted_quantity == 0


@pytest.mark.django_db
def test_empty_items_returns_400(auth_client):
    response = auth_client.post(
        "/api/v1/invoices",
        {
            "items": [],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_REQUEST"
    assert response.data["message"] == "At least one item is required"
    assert Invoice.objects.count() == 0


@pytest.mark.django_db
def test_non_moderated_sku_returns_400(
    auth_client,
    seller,
    category,
):
    product = create_product(
        seller,
        category,
        status=ProductStatus.ON_MODERATION,
    )
    sku = create_sku(product)

    response = auth_client.post(
        "/api/v1/invoices",
        {
            "items": [
                {
                    "sku_id": str(sku.uuid),
                    "quantity": 10,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "Invoice can only be created for MODERATED products",
    }
    assert Invoice.objects.count() == 0


@pytest.mark.django_db
def test_others_sku_returns_403(
    auth_client,
    category,
):
    other_seller = SellerFactory()
    product = create_product(
        other_seller,
        category,
        slug="other-iphone",
    )
    sku = create_sku(
        product,
        article="other-iphone-15-256-black",
    )

    response = auth_client.post(
        "/api/v1/invoices",
        {
            "items": [
                {
                    "sku_id": str(sku.uuid),
                    "quantity": 10,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 403
    assert response.data == {
        "code": "NOT_OWNER",
        "message": "One or more SKUs do not belong to the authenticated seller",
    }
    assert Invoice.objects.count() == 0
