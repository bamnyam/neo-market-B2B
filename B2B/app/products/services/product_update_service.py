from dataclasses import dataclass

from django.db import transaction

from app.categories.models import Category
from app.products.errors.product_hard_blocked_error import ProductHardBlockedError
from app.products.errors.product_not_found_error import ProductNotFoundError
from app.products.errors.product_not_owner_error import ProductNotOwnerError
from app.products.models import (
    Product,
    ProductCharacteristics,
    ProductImages,
    ProductStatus,
)
from app.skus.integration.moderation_events import ModerationEventsClient


@dataclass(frozen=True)
class ProductUpdateResult:
    product: Product


class ProductUpdateService:
    def __init__(
        self,
        moderation_events_client=None,
    ):
        self.moderation_events_client = (
            moderation_events_client or ModerationEventsClient()
        )

    @transaction.atomic
    def update_product(
        self,
        *,
        product_uuid,
        seller,
        data,
    ) -> ProductUpdateResult:
        try:
            product = (
                Product.objects.select_for_update()
                .select_related("seller", "category")
                .get(uuid=product_uuid)
            )
        except Product.DoesNotExist:
            raise ProductNotFoundError

        if product.seller_id != seller.id:
            raise ProductNotOwnerError

        if product.status == ProductStatus.HARD_BLOCKED:
            raise ProductHardBlockedError

        category_uuid = data.pop("category_id", None)
        images = data.pop("images", None)
        characteristics = data.pop("characteristics", None)

        if category_uuid is not None:
            product.category = Category.objects.get(uuid=category_uuid)

        for field in (
            "title",
            "slug",
            "description",
        ):
            if field in data:
                setattr(product, field, data[field])

        should_emit_edited = product.status in (
            ProductStatus.MODERATED,
            ProductStatus.BLOCKED,
        )

        if should_emit_edited:
            product.status = ProductStatus.ON_MODERATION

        product.save()

        if images is not None:
            product.images.all().delete()
            ProductImages.objects.bulk_create(
                [
                    ProductImages(
                        product=product,
                        url=image["url"],
                        ordering=image["ordering"],
                    )
                    for image in images
                ]
            )

        if characteristics is not None:
            product.characteristics.all().delete()
            ProductCharacteristics.objects.bulk_create(
                [
                    ProductCharacteristics(
                        product=product,
                        name=characteristic["name"],
                        value=characteristic["value"],
                    )
                    for characteristic in characteristics
                ]
            )

        if should_emit_edited:
            self.moderation_events_client.emit_product_edited(product)

        return ProductUpdateResult(product=product)
