import uuid

from app.skus.api.serializers import (
    SkuCreateSerializer,
    SkuResponseSerializer,
)


def test_sku_create_serializer_accepts_valid_payload():
    product_id = uuid.uuid4()

    serializer = SkuCreateSerializer(
        data={
            "product_id": str(product_id),
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
    )

    assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["product_id"] == product_id
    assert serializer.validated_data["name"] == "256GB Black"
    assert serializer.validated_data["price"] == 12999000
    assert serializer.validated_data["cost_price"] == 9500000
    assert serializer.validated_data["discount"] == 0
    assert serializer.validated_data["image"] == "/s3/iphone15-black-256.jpg"
    assert serializer.validated_data["characteristics"] == [
        {
            "name": "Цвет",
            "value": "Чёрный",
        },
        {
            "name": "Объём памяти",
            "value": "256 ГБ",
        },
    ]


def test_sku_create_serializer_sets_default_discount_and_characteristics():
    product_id = uuid.uuid4()

    serializer = SkuCreateSerializer(
        data={
            "product_id": str(product_id),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["discount"] == 0
    assert serializer.validated_data["characteristics"] == []


def test_sku_create_serializer_rejects_invalid_product_id():
    serializer = SkuCreateSerializer(
        data={
            "product_id": "invalid-product-id",
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "product_id" in serializer.errors


def test_sku_create_serializer_rejects_empty_name():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "name" in serializer.errors


def test_sku_create_serializer_rejects_missing_name():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "name" in serializer.errors


def test_sku_create_serializer_rejects_non_positive_price():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 0,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "price" in serializer.errors


def test_sku_create_serializer_rejects_non_positive_cost_price():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 0,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "cost_price" in serializer.errors


def test_sku_create_serializer_rejects_negative_discount():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": -1,
            "image": "/s3/iphone15-black-256.jpg",
        }
    )

    assert not serializer.is_valid()
    assert "discount" in serializer.errors


def test_sku_create_serializer_rejects_missing_image():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
        }
    )

    assert not serializer.is_valid()
    assert "image" in serializer.errors


def test_sku_create_serializer_rejects_empty_image():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "",
        }
    )

    assert not serializer.is_valid()
    assert "image" in serializer.errors


def test_sku_create_serializer_accepts_empty_characteristics():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [],
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["characteristics"] == []


def test_sku_create_serializer_rejects_characteristic_without_name():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [
                {
                    "value": "Чёрный",
                }
            ],
        }
    )

    assert not serializer.is_valid()
    assert "characteristics" in serializer.errors


def test_sku_create_serializer_rejects_characteristic_without_value():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "image": "/s3/iphone15-black-256.jpg",
            "characteristics": [
                {
                    "name": "Цвет",
                }
            ],
        }
    )

    assert not serializer.is_valid()
    assert "characteristics" in serializer.errors


def test_sku_response_serializer_returns_expected_payload():
    sku_id = uuid.uuid4()
    product_id = uuid.uuid4()
    characteristic_id = uuid.uuid4()

    serializer = SkuResponseSerializer(
        {
            "id": sku_id,
            "product_id": product_id,
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "active_quantity": 0,
            "reserved_quantity": 0,
            "characteristics": [
                {
                    "id": characteristic_id,
                    "name": "Цвет",
                    "value": "Чёрный",
                }
            ],
        }
    )

    data = serializer.data

    assert data == {
        "id": str(sku_id),
        "product_id": str(product_id),
        "name": "256GB Black",
        "price": 12999000,
        "cost_price": 9500000,
        "discount": 0,
        "image": "/s3/iphone15-black-256.jpg",
        "active_quantity": 0,
        "reserved_quantity": 0,
        "characteristics": [
            {
                "id": str(characteristic_id),
                "name": "Цвет",
                "value": "Чёрный",
            }
        ],
    }
