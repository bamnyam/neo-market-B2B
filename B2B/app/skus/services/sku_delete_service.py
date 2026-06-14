from dataclasses import dataclass

from django.db import transaction

from app.products.models import ProductStatus
from app.skus.errors.sku_delete_active_reserves_error import (
    SkuDeleteActiveReservesError,
)
from app.skus.errors.sku_delete_hard_blocked_error import (
    SkuDeleteHardBlockedError,
)
from app.skus.errors.sku_delete_not_found_error import SkuDeleteNotFoundError
from app.skus.errors.sku_delete_not_owner_error import SkuDeleteNotOwnerError
from app.skus.integration.moderation_events import ModerationEventsClient
from app.skus.integration.sku_events import SkuEventsClient
from app.skus.models import Sku


@dataclass(frozen=True)
class SkuDeleteResult:
    ok: bool = True


class SkuDeleteService:
    def __init__(
        self,
        *,
        moderation_events_client=None,
        sku_events_client=None,
    ):
        self.moderation_events_client = (
            moderation_events_client or ModerationEventsClient()
        )
        self.sku_events_client = sku_events_client or SkuEventsClient()

    @transaction.atomic
    def delete_sku(
        self,
        *,
        sku_uuid,
        seller,
    ) -> SkuDeleteResult:
        try:
            sku = (
                Sku.objects.select_for_update()
                .select_related("product", "product__seller")
                .get(uuid=sku_uuid)
            )
        except Sku.DoesNotExist:
            raise SkuDeleteNotFoundError

        product = sku.product

        if product.seller_id != seller.id:
            raise SkuDeleteNotOwnerError

        if product.status == ProductStatus.HARD_BLOCKED:
            raise SkuDeleteHardBlockedError

        if sku.reserved_quantity > 0:
            raise SkuDeleteActiveReservesError

        should_emit_out_of_stock = (
            sku.active_quantity > 0 and product.status == ProductStatus.MODERATED
        )

        sku.delete()

        is_last_sku = not Sku.objects.filter(product=product).exists()

        if is_last_sku and product.status == ProductStatus.ON_MODERATION:
            product.status = ProductStatus.CREATED
            product.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            self.moderation_events_client.emit_product_deleted(product)

        if should_emit_out_of_stock:
            self.sku_events_client.emit_sku_out_of_stock(
                sku,
                available_quantity=0,
            )

        return SkuDeleteResult()
