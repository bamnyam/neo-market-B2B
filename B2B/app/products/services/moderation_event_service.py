from dataclasses import dataclass

from django.db import IntegrityError, transaction

from app.products.integration.b2c_events import B2CProductEventsClient
from app.products.models import (
    ProcessedModerationEvent,
    Product,
    ProductFieldReport,
    ProductStatus,
)
from app.skus.models import Sku


@dataclass(frozen=True)
class ModerationEventResult:
    processed: bool


class ModerationEventService:
    def __init__(
        self,
        b2c_events_client=None,
    ):
        self.b2c_events_client = b2c_events_client or B2CProductEventsClient()

    @transaction.atomic
    def apply(self, data) -> ModerationEventResult:
        idempotency_key = data["idempotency_key"]
        event_type = data["event_type"]

        try:
            with transaction.atomic():
                ProcessedModerationEvent.objects.create(
                    sender_service=data["sender_service"],
                    idempotency_key=idempotency_key,
                    product_id=data["product_id"],
                    status=event_type,
                )
        except IntegrityError:
            return ModerationEventResult(processed=False)

        product = (
            Product.objects.select_for_update()
            .prefetch_related("skus")
            .get(uuid=data["product_id"])
        )

        if event_type == ProductStatus.MODERATED:
            self._apply_moderated(product)
            return ModerationEventResult(processed=True)

        self._apply_blocked(product, data)
        self.b2c_events_client.emit_product_blocked(product)

        return ModerationEventResult(processed=True)

    def _apply_moderated(self, product):
        product.status = ProductStatus.MODERATED
        product.blocking_reason_id = None
        product.blocking_reason_title = None
        product.moderator_comment = None
        product.save(
            update_fields=[
                "status",
                "blocking_reason_id",
                "blocking_reason_title",
                "moderator_comment",
                "updated_at",
            ]
        )
        product.field_reports.all().delete()

    def _apply_blocked(self, product, data):
        product.status = (
            ProductStatus.HARD_BLOCKED
            if data.get("hard_block")
            else ProductStatus.BLOCKED
        )
        product.blocking_reason_id = data["blocking_reason_id"]
        product.blocking_reason_title = ""
        product.moderator_comment = data.get("moderator_comment") or ""
        product.save(
            update_fields=[
                "status",
                "blocking_reason_id",
                "blocking_reason_title",
                "moderator_comment",
                "updated_at",
            ]
        )

        product.field_reports.all().delete()
        field_reports = data.get("field_reports") or []
        sku_ids = {
            sku.uuid: sku.id
            for sku in Sku.objects.filter(
                product=product,
                uuid__in=[
                    report["sku_id"]
                    for report in field_reports
                    if report.get("sku_id") is not None
                ],
            )
        }

        ProductFieldReport.objects.bulk_create(
            [
                ProductFieldReport(
                    product=product,
                    sku_id=sku_ids.get(report.get("sku_id")),
                    field_name=report["field_name"],
                    comment=report["comment"],
                )
                for report in field_reports
            ]
        )
