import uuid
from datetime import UTC, datetime

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
            "article": "iphone-15-256-black",
            "images": [
                {
                    "url": "/s3/iphone15-black-front.jpg",
                    "ordering": 0,
                },
                {
                    "url": "/s3/iphone15-black-back.jpg",
                    "ordering": 1,
                },
            ],
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
    assert serializer.validated_data["article"] == ("iphone-15-256-black")

    assert serializer.validated_data["images"] == [
        {
            "url": "/s3/iphone15-black-front.jpg",
            "ordering": 0,
        },
        {
            "url": "/s3/iphone15-black-back.jpg",
            "ordering": 1,
        },
    ]

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


def test_sku_create_serializer_sets_default_values():

    product_id = uuid.uuid4()

    serializer = SkuCreateSerializer(
        data={
            "product_id": str(product_id),
            "name": "256GB Black",
            "price": 12999000,
            "article": "iphone-15-256-black",
        }
    )

    assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["discount"] == 0

    assert serializer.validated_data["images"] == []

    assert serializer.validated_data["characteristics"] == []

    assert "cost_price" not in serializer.validated_data


def test_sku_create_serializer_accepts_zero_price():

    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 0,
            "article": "iphone-15-256-black",
        }
    )

    assert serializer.is_valid(), serializer.errors


def test_sku_create_serializer_accepts_null_cost_price():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": None,
            "article": "iphone-15-256-black",
        }
    )

    assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["cost_price"] is None


def test_sku_create_serializer_rejects_invalid_product_id():
    serializer = SkuCreateSerializer(
        data={
            "product_id": "invalid-product-id",
            "name": "256GB Black",
            "price": 12999000,
            "article": "iphone-15-256-black",
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
            "article": "iphone-15-256-black",
        }
    )

    assert not serializer.is_valid()
    assert "name" in serializer.errors


def test_sku_create_serializer_rejects_missing_name():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "price": 12999000,
            "article": "iphone-15-256-black",
        }
    )

    assert not serializer.is_valid()
    assert "name" in serializer.errors


def test_sku_create_serializer_rejects_negative_price():

    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": -1,
            "article": "iphone-15-256-black",
        }
    )

    assert not serializer.is_valid()

    assert "price" in serializer.errors


def test_sku_create_serializer_accepts_zero_cost_price():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 0,
            "article": "iphone-15-256-black",
        }
    )

    assert serializer.is_valid(), serializer.errors


def test_sku_create_serializer_rejects_negative_cost_price():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": -1,
            "article": "iphone-15-256-black",
        }
    )

    assert not serializer.is_valid()
    assert "cost_price" not in serializer.validated_data


def test_sku_create_serializer_rejects_negative_discount():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": -1,
            "article": "iphone-15-256-black",
        }
    )

    assert not serializer.is_valid()
    assert "discount" in serializer.errors


def test_sku_create_serializer_rejects_missing_article():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
        }
    )

    assert not serializer.is_valid()
    assert "article" in serializer.errors


def test_sku_create_serializer_rejects_empty_article():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "article": "",
        }
    )

    assert not serializer.is_valid()
    assert "article" in serializer.errors


def test_sku_create_serializer_accepts_empty_images():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "article": "iphone-15-256-black",
            "images": [],
        }
    )

    assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["images"] == []


def test_sku_create_serializer_rejects_image_without_url():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "article": "iphone-15-256-black",
            "images": [
                {
                    "ordering": 0,
                }
            ],
        }
    )

    assert not serializer.is_valid()
    assert "images" in serializer.errors


def test_sku_create_serializer_rejects_characteristic_without_name():
    serializer = SkuCreateSerializer(
        data={
            "product_id": str(uuid.uuid4()),
            "name": "256GB Black",
            "price": 12999000,
            "article": "iphone-15-256-black",
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
            "article": "iphone-15-256-black",
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

    image_id = uuid.uuid4()
    characteristic_id = uuid.uuid4()

    created_at = datetime.now(UTC)
    updated_at = datetime.now(UTC)

    serializer = SkuResponseSerializer(
        {
            "id": sku_id,
            "product_id": product_id,
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "stock_quantity": 10,
            "active_quantity": 8,
            "reserved_quantity": 2,
            "article": "iphone-15-256-black",
            "created_at": created_at,
            "updated_at": updated_at,
            "images": [
                {
                    "id": image_id,
                    "url": "/s3/iphone15-black.jpg",
                    "ordering": 0,
                }
            ],
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
        "stock_quantity": 10,
        "active_quantity": 8,
        "reserved_quantity": 2,
        "article": "iphone-15-256-black",
        "created_at": created_at.isoformat().replace(
            "+00:00",
            "Z",
        ),
        "updated_at": updated_at.isoformat().replace(
            "+00:00",
            "Z",
        ),
        "images": [
            {
                "id": str(image_id),
                "url": "/s3/iphone15-black.jpg",
                "ordering": 0,
            }
        ],
        "characteristics": [
            {
                "id": str(characteristic_id),
                "name": "Цвет",
                "value": "Чёрный",
            }
        ],
    }
