from dataclasses import dataclass

from django.db import transaction

from app.products.errors.product_already_deleted_error import ProductAlreadyDeletedError
from app.products.errors.product_hard_blocked_error import ProductHardBlockedError
from app.products.errors.product_not_found_error import ProductNotFoundError
from app.products.errors.product_not_owner_error import ProductNotOwnerError
from app.products.integration.product_events import ProductEventsClient
from app.products.models import Product, ProductStatus


@dataclass(frozen=True)
class ProductDeleteResult:
    ok: bool = True


class ProductDeleteService:
    def __init__(
        self,
        events_client=None,
    ):
        self.events_client = events_client or ProductEventsClient()

    @transaction.atomic
    def delete_product(
        self,
        *,
        product_uuid,
        seller,
    ) -> ProductDeleteResult:
        try:
            product = (
                Product.objects.select_related("seller")
                .prefetch_related("skus")
                .get(uuid=product_uuid)
            )
        except Product.DoesNotExist:
            raise ProductNotFoundError

        if product.seller_id != seller.id:
            raise ProductNotOwnerError

        if product.deleted:
            raise ProductAlreadyDeletedError

        if product.status == ProductStatus.HARD_BLOCKED:
            raise ProductHardBlockedError

        product.deleted = True
        product.save(update_fields=["deleted", "updated_at"])

        self.events_client.emit_product_deleted(product)

        return ProductDeleteResult()
