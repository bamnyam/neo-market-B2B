import uuid

import pytest

from app.products.models import Product, ProductStatus
from app.skus.errors.invalid_sku_request_error import InvalidSkuRequestError
from app.skus.errors.product_hard_blocked_error import ProductHardBlockedError
from app.skus.errors.product_not_found_error import ProductNotFoundError
from app.skus.errors.product_not_owner_error import ProductNotOwnerError
from app.skus.models import Sku, SkuCharacteristics, SkuImages
from app.skus.services.sku_create_service import SkuCreateService
from tests.factories.category_factory import CategoryFactory
from tests.factories.seller_factory import SellerFactory


class FakeModerationEventsClient:
    def __init__(self):
        self.created_events = []

    def emit_product_created(self, product):
        self.created_events.append(product)


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
def product(seller, category):
    return Product.objects.create(
        seller=seller,
        category=category,
        title="iPhone 15",
        slug="iphone-15",
        description="desc",
        status=ProductStatus.CREATED,
    )


@pytest.fixture
def moderation_events_client():
    return FakeModerationEventsClient()


@pytest.fixture
def service(moderation_events_client):
    return SkuCreateService(
        moderation_events_client=moderation_events_client,
    )


def valid_sku_data(product):
    return {
        "product_id": product.uuid,
        "name": "256GB Black",
        "price": 12999000,
        "cost_price": 9500000,
        "discount": 0,
        "image": "/s3/iphone15-black-256.jpg",
        "characteristics": [
            {
                "name": "Цвет",
                "value": "Чёрный",
            },
            {
                "name": "Объём памяти",
                "value": "256 ГБ",
            },
        ],
    }


@pytest.mark.django_db
def test_create_sku_creates_sku_with_image_and_characteristics(
    service,
    seller,
    product,
):
    result = service.create_sku(
        seller=seller,
        data=valid_sku_data(product),
    )

    sku = result.sku

    assert Sku.objects.count() == 1
    assert SkuImages.objects.count() == 1
    assert SkuCharacteristics.objects.count() == 2

    assert sku.product == product
    assert sku.name == "256GB Black"
    assert int(sku.price) == 12999000
    assert int(sku.cost_price) == 9500000
    assert int(sku.discount) == 0
    assert sku.stock_quantity == 0
    assert sku.active_quantity == 0
    assert sku.reserved_quantity == 0
    assert sku.article is not None

    image = SkuImages.objects.get(sku=sku)

    assert image.url == "/s3/iphone15-black-256.jpg"
    assert image.ordering == 0

    characteristics = list(SkuCharacteristics.objects.filter(sku=sku).order_by("id"))

    assert characteristics[0].name == "Цвет"
    assert characteristics[0].value == "Чёрный"
    assert characteristics[1].name == "Объём памяти"
    assert characteristics[1].value == "256 ГБ"


@pytest.mark.django_db
def test_first_sku_transitions_product_to_on_moderation(
    service,
    seller,
    product,
):
    service.create_sku(
        seller=seller,
        data=valid_sku_data(product),
    )

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION


@pytest.mark.django_db
def test_first_sku_emits_created_event_to_moderation(
    service,
    seller,
    product,
    moderation_events_client,
):
    service.create_sku(
        seller=seller,
        data=valid_sku_data(product),
    )

    assert moderation_events_client.created_events == [product]


@pytest.mark.django_db
def test_second_sku_no_state_change(
    service,
    seller,
    product,
    moderation_events_client,
):
    product.status = ProductStatus.ON_MODERATION
    product.save(update_fields=["status"])

    Sku.objects.create(
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

    service.create_sku(
        seller=seller,
        data={
            **valid_sku_data(product),
            "name": "256GB Black",
            "image": "/s3/iphone15-black-256.jpg",
        },
    )

    product.refresh_from_db()

    assert product.status == ProductStatus.ON_MODERATION
    assert Sku.objects.count() == 2
    assert moderation_events_client.created_events == []


@pytest.mark.django_db
def test_created_product_with_existing_sku_does_not_emit_event(
    service,
    seller,
    product,
    moderation_events_client,
):
    Sku.objects.create(
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

    service.create_sku(
        seller=seller,
        data={
            **valid_sku_data(product),
            "name": "256GB Black",
            "image": "/s3/iphone15-black-256.jpg",
        },
    )

    product.refresh_from_db()

    assert product.status == ProductStatus.CREATED
    assert Sku.objects.count() == 2
    assert moderation_events_client.created_events == []


@pytest.mark.django_db
def test_add_sku_to_hard_blocked_raises_error(
    service,
    seller,
    product,
    moderation_events_client,
):
    product.status = ProductStatus.HARD_BLOCKED
    product.save(update_fields=["status"])

    with pytest.raises(ProductHardBlockedError):
        service.create_sku(
            seller=seller,
            data=valid_sku_data(product),
        )

    product.refresh_from_db()

    assert product.status == ProductStatus.HARD_BLOCKED
    assert Sku.objects.count() == 0
    assert SkuImages.objects.count() == 0
    assert SkuCharacteristics.objects.count() == 0
    assert moderation_events_client.created_events == []


@pytest.mark.django_db
def test_add_sku_to_missing_product_raises_error(
    service,
    seller,
    moderation_events_client,
):
    data = {
        "product_id": uuid.uuid4(),
        "name": "256GB Black",
        "price": 12999000,
        "cost_price": 9500000,
        "discount": 0,
        "image": "/s3/iphone15-black-256.jpg",
        "characteristics": [],
    }

    with pytest.raises(ProductNotFoundError):
        service.create_sku(
            seller=seller,
            data=data,
        )

    assert Sku.objects.count() == 0
    assert moderation_events_client.created_events == []


@pytest.mark.django_db
def test_add_sku_to_other_seller_product_raises_error(
    service,
    seller,
    other_seller,
    category,
    moderation_events_client,
):
    product = Product.objects.create(
        seller=other_seller,
        category=category,
        title="Other iPhone",
        slug="other-iphone",
        description="desc",
        status=ProductStatus.CREATED,
    )

    with pytest.raises(ProductNotOwnerError):
        service.create_sku(
            seller=seller,
            data=valid_sku_data(product),
        )

    assert Sku.objects.count() == 0
    assert moderation_events_client.created_events == []


@pytest.mark.django_db
def test_empty_name_raises_invalid_request_error(
    service,
    seller,
    product,
):
    data = {
        **valid_sku_data(product),
        "name": "",
    }

    with pytest.raises(InvalidSkuRequestError) as exc_info:
        service.create_sku(
            seller=seller,
            data=data,
        )

    assert exc_info.value.message == "name is required"
    assert Sku.objects.count() == 0


@pytest.mark.django_db
def test_non_positive_price_raises_invalid_request_error(
    service,
    seller,
    product,
):
    data = {
        **valid_sku_data(product),
        "price": 0,
    }

    with pytest.raises(InvalidSkuRequestError) as exc_info:
        service.create_sku(
            seller=seller,
            data=data,
        )

    assert exc_info.value.message == "price must be a positive integer (kopecks)"
    assert Sku.objects.count() == 0


@pytest.mark.django_db
def test_non_positive_cost_price_raises_invalid_request_error(
    service,
    seller,
    product,
):
    data = {
        **valid_sku_data(product),
        "cost_price": 0,
    }

    with pytest.raises(InvalidSkuRequestError) as exc_info:
        service.create_sku(
            seller=seller,
            data=data,
        )

    assert exc_info.value.message == "cost_price must be a positive integer (kopecks)"
    assert Sku.objects.count() == 0


@pytest.mark.django_db
def test_missing_image_raises_invalid_request_error(
    service,
    seller,
    product,
):
    data = {
        **valid_sku_data(product),
        "image": "",
    }

    with pytest.raises(InvalidSkuRequestError) as exc_info:
        service.create_sku(
            seller=seller,
            data=data,
        )

    assert exc_info.value.message == "image is required"
    assert Sku.objects.count() == 0
