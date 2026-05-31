from dataclasses import dataclass

from django.db import transaction

from app.products.models import ProductStatus
from app.skus.errors.sku_not_found_error import SkuNotFoundError
from app.skus.errors.sku_product_hard_blocked_error import (
    SkuProductHardBlockedError,
)
from app.skus.errors.sku_product_not_owner_error import SkuProductNotOwnerError
from app.skus.integration.moderation_events import ModerationEventsClient
from app.skus.models import (
    Sku,
    SkuCharacteristics,
    SkuImages,
)


@dataclass(frozen=True)
class SkuUpdateResult:
    sku: Sku


class SkuUpdateService:
    def __init__(
        self,
        moderation_events_client=None,
    ):
        self.moderation_events_client = (
            moderation_events_client or ModerationEventsClient()
        )

    @transaction.atomic
    def update_sku(
        self,
        *,
        sku_uuid,
        seller,
        data,
    ) -> SkuUpdateResult:
        try:
            sku = (
                Sku.objects.select_for_update()
                .select_related("product", "product__seller")
                .get(uuid=sku_uuid)
            )
        except Sku.DoesNotExist:
            raise SkuNotFoundError

        product = sku.product

        if product.seller_id != seller.id:
            raise SkuProductNotOwnerError

        if product.status == ProductStatus.HARD_BLOCKED:
            raise SkuProductHardBlockedError

        images = data.pop("images", None)
        image = data.pop("image", None)
        characteristics = data.pop("characteristics", None)

        for field in (
            "name",
            "price",
            "cost_price",
            "discount",
            "article",
        ):
            if field in data:
                setattr(sku, field, data[field] if data[field] is not None else 0)

        sku.save()

        if image is not None:
            images = [
                {
                    "url": image,
                    "ordering": 0,
                }
            ]

        if images is not None:
            sku.images.all().delete()
            SkuImages.objects.bulk_create(
                [
                    SkuImages(
                        sku=sku,
                        url=image_data["url"],
                        ordering=image_data.get("ordering", 0),
                    )
                    for image_data in images
                ]
            )

        if characteristics is not None:
            sku.characteristics.all().delete()
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

        should_emit_edited = product.status in (
            ProductStatus.MODERATED,
            ProductStatus.BLOCKED,
        )

        if should_emit_edited:
            product.status = ProductStatus.ON_MODERATION
            product.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            self.moderation_events_client.emit_product_edited(product)

        return SkuUpdateResult(sku=sku)
