import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.products.models import Product, ProductImages, ProductStatus
from app.skus.models import Sku
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def catalog_client(client):
    client.credentials(HTTP_X_SERVICE_KEY=settings.B2B_TO_B2C_KEY)
    return client


@pytest.fixture
def seller():
    return SellerFactory()


@pytest.fixture
def category():
    return CategoryFactory()


def make_product(
    *,
    seller,
    category,
    slug,
    status=ProductStatus.MODERATED,
    deleted=False,
    active_quantity=5,
):
    product = Product.objects.create(
        seller=seller,
        category=category,
        title=f"Product {slug}",
        slug=slug,
        description="Catalog product",
        status=status,
        deleted=deleted,
    )
    ProductImages.objects.create(
        product=product,
        url=f"/s3/{slug}.jpg",
        ordering=0,
    )
    sku = Sku.objects.create(
        product=product,
        name=f"SKU {slug}",
        price=100000,
        discount=0,
        cost_price=70000,
        stock_quantity=active_quantity,
        active_quantity=active_quantity,
        reserved_quantity=2,
        article=f"{slug}-sku",
    )

    return product, sku


@pytest.mark.django_db
def test_catalog_returns_moderated_in_stock_products(
    catalog_client,
    seller,
    category,
):
    visible, _ = make_product(
        seller=seller,
        category=category,
        slug="visible",
    )
    created, _ = make_product(
        seller=seller,
        category=category,
        slug="created",
        status=ProductStatus.CREATED,
    )
    deleted, _ = make_product(
        seller=seller,
        category=category,
        slug="deleted",
        deleted=True,
    )
    out_of_stock, _ = make_product(
        seller=seller,
        category=category,
        slug="out-of-stock",
        active_quantity=0,
    )

    response = catalog_client.get("/api/v1/products")

    assert response.status_code == 200, response.data

    product_ids = {item["id"] for item in response.data["items"]}

    assert product_ids == {str(visible.uuid)}
    assert str(created.uuid) not in product_ids
    assert str(deleted.uuid) not in product_ids
    assert str(out_of_stock.uuid) not in product_ids
    assert response.data["total_count"] == 1


@pytest.mark.django_db
def test_catalog_excludes_hard_blocked(
    catalog_client,
    seller,
    category,
):
    visible, _ = make_product(
        seller=seller,
        category=category,
        slug="visible-hard-block-check",
    )
    hard_blocked, _ = make_product(
        seller=seller,
        category=category,
        slug="hard-blocked",
        status=ProductStatus.HARD_BLOCKED,
    )

    response = catalog_client.get("/api/v1/products")

    assert response.status_code == 200, response.data

    product_ids = {item["id"] for item in response.data["items"]}

    assert product_ids == {str(visible.uuid)}
    assert str(hard_blocked.uuid) not in product_ids


@pytest.mark.django_db
def test_catalog_missing_service_key_returns_401(client):
    response = client.get("/api/v1/products")

    assert response.status_code == 401
    assert response.data["code"] == "UNAUTHORIZED"


@pytest.mark.django_db
def test_catalog_response_has_no_cost_price(
    catalog_client,
    seller,
    category,
):
    product, _ = make_product(
        seller=seller,
        category=category,
        slug="no-cost-price",
    )

    list_response = catalog_client.get("/api/v1/products")
    detail_response = catalog_client.get(f"/api/v1/products/{product.uuid}")

    assert list_response.status_code == 200, list_response.data
    assert detail_response.status_code == 200, detail_response.data
    assert "cost_price" not in _keys_in(list_response.data)
    assert "reserved_quantity" not in _keys_in(list_response.data)
    assert "cost_price" not in _keys_in(detail_response.data)
    assert "reserved_quantity" not in _keys_in(detail_response.data)
    assert detail_response.data["skus"][0]["active_quantity"] == 5


@pytest.mark.django_db
def test_batch_ids_returns_visible_subset(
    catalog_client,
    seller,
    category,
):
    visible, _ = make_product(
        seller=seller,
        category=category,
        slug="batch-visible",
    )
    hard_blocked, _ = make_product(
        seller=seller,
        category=category,
        slug="batch-hard-blocked",
        status=ProductStatus.HARD_BLOCKED,
    )
    out_of_stock, _ = make_product(
        seller=seller,
        category=category,
        slug="batch-out-of-stock",
        active_quantity=0,
    )

    response = catalog_client.get(
        "/api/v1/products",
        {
            "ids": ",".join(
                [
                    str(visible.uuid),
                    str(hard_blocked.uuid),
                    str(out_of_stock.uuid),
                ]
            )
        },
    )

    assert response.status_code == 200, response.data
    assert [item["id"] for item in response.data["items"]] == [str(visible.uuid)]
    assert response.data["total_count"] == 1


@pytest.mark.django_db
def test_catalog_filters_by_category_and_search(
    catalog_client,
    seller,
    category,
):
    other_category = CategoryFactory()
    matched, _ = make_product(
        seller=seller,
        category=category,
        slug="catalog-search-match",
    )
    Product.objects.filter(id=matched.id).update(
        title="Blue Phone",
        description="Visible by description",
    )
    wrong_category, _ = make_product(
        seller=seller,
        category=other_category,
        slug="catalog-search-wrong-category",
    )
    Product.objects.filter(id=wrong_category.id).update(
        title="Blue Phone",
        description="Visible by description",
    )

    response = catalog_client.get(
        "/api/v1/products",
        {
            "category": str(category.uuid),
            "search": "description",
        },
    )

    assert response.status_code == 200, response.data
    assert [item["id"] for item in response.data["items"]] == [str(matched.uuid)]


@pytest.mark.django_db
def test_catalog_sorts_by_price_asc(
    catalog_client,
    seller,
    category,
):
    expensive, expensive_sku = make_product(
        seller=seller,
        category=category,
        slug="catalog-expensive",
    )
    cheap, cheap_sku = make_product(
        seller=seller,
        category=category,
        slug="catalog-cheap",
    )
    expensive_sku.price = 200000
    expensive_sku.save(update_fields=["price"])
    cheap_sku.price = 100000
    cheap_sku.save(update_fields=["price"])

    response = catalog_client.get(
        "/api/v1/products",
        {"sort": "price_asc"},
    )

    assert response.status_code == 200, response.data
    assert [item["id"] for item in response.data["items"]] == [
        str(cheap.uuid),
        str(expensive.uuid),
    ]


@pytest.mark.django_db
def test_catalog_invalid_sort_returns_400(catalog_client):
    response = catalog_client.get(
        "/api/v1/products",
        {"sort": "unknown"},
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "sort must be one of price_asc, price_desc, date_desc",
        "field": "sort",
    }


@pytest.mark.django_db
def test_catalog_invalid_offset_returns_400(catalog_client):
    response = catalog_client.get(
        "/api/v1/products",
        {"offset": "-1"},
    )

    assert response.status_code == 400
    assert response.data == {
        "code": "INVALID_REQUEST",
        "message": "offset must be greater than or equal to 0",
        "field": "offset",
    }


def _keys_in(value):
    if isinstance(value, dict):
        keys = set(value.keys())
        for item in value.values():
            keys.update(_keys_in(item))
        return keys

    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_keys_in(item))
        return keys

    return set()
