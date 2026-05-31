from dataclasses import dataclass

from django.db import transaction

from app.products.models import Product, ProductStatus
from app.skus.errors.invalid_sku_request_error import (
    InvalidSkuRequestError,
)
from app.skus.errors.product_hard_blocked_error import (
    ProductHardBlockedError,
)
from app.skus.errors.product_not_found_error import (
    ProductNotFoundError,
)
from app.skus.errors.product_not_owner_error import (
    ProductNotOwnerError,
)
from app.skus.integration.moderation_events import (
    ModerationEventsClient,
)
from app.skus.models import (
    Sku,
    SkuCharacteristics,
    SkuImages,
)


@dataclass(frozen=True)
class SkuCreateResult:
    sku: Sku


class SkuCreateService:
    def __init__(
        self,
        moderation_events_client=None,
    ):
        self.moderation_events_client = (
            moderation_events_client or ModerationEventsClient()
        )

    @transaction.atomic
    def create_sku(
        self,
        *,
        seller,
        data,
    ) -> SkuCreateResult:

        product_uuid = data["product_id"]

        try:
            product = (
                Product.objects.select_for_update()
                .select_related("seller")
                .get(uuid=product_uuid)
            )

        except Product.DoesNotExist:
            raise ProductNotFoundError

        if product.seller_id != seller.id:
            raise ProductNotOwnerError

        if product.status == ProductStatus.HARD_BLOCKED:
            raise ProductHardBlockedError

        name = data["name"]

        price = data["price"]

        cost_price = data.get("cost_price")

        discount = data.get("discount", 0)

        article = data["article"]

        images = data.get("images", [])

        characteristics = data.get(
            "characteristics",
            [],
        )

        if not name:
            raise InvalidSkuRequestError("name is required")

        if price <= 0:
            raise InvalidSkuRequestError("price must be a positive integer (kopecks)")

        if cost_price is not None and cost_price < 0:
            raise InvalidSkuRequestError(
                "cost_price must be greater than or equal to 0"
            )

        if not article:
            raise InvalidSkuRequestError("article is required")

        is_first_sku = not product.skus.exists()

        sku = Sku.objects.create(
            product=product,
            name=name,
            price=price,
            cost_price=(cost_price if cost_price is not None else 0),
            discount=discount,
            stock_quantity=0,
            active_quantity=0,
            reserved_quantity=0,
            article=article,
        )

        if images:
            SkuImages.objects.bulk_create(
                [
                    SkuImages(
                        sku=sku,
                        url=image["url"],
                        ordering=image.get(
                            "ordering",
                            0,
                        ),
                    )
                    for image in images
                ]
            )

        if characteristics:
            SkuCharacteristics.objects.bulk_create(
                [
                    SkuCharacteristics(
                        sku=sku,
                        name=characteristic["name"],
                        value=characteristic["value"],
                    )
                    for characteristic in characteristics
                ]
            )

        event_type = None

        if is_first_sku and product.status == ProductStatus.CREATED:
            event_type = "CREATED"

        elif product.status in (
            ProductStatus.MODERATED,
            ProductStatus.BLOCKED,
        ):
            event_type = "UPDATED"

        if event_type:
            product.status = ProductStatus.ON_MODERATION

            product.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            if event_type == "CREATED":
                self.moderation_events_client.emit_product_created(product)

            else:
                self.moderation_events_client.emit_product_updated(product)

        return SkuCreateResult(sku=sku)
