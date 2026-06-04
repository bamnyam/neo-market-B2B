from dataclasses import dataclass

from django.db import transaction

from app.skus.integration.sku_events import SkuEventsClient
from app.skus.models import ReserveOperation, Sku, UnreserveOperation


@dataclass(frozen=True)
class ReserveConflictError(Exception):
    failed_items: list[dict]


@dataclass(frozen=True)
class UnreserveConflictError(Exception):
    failed_items: list[dict]


class ReserveService:
    def __init__(self, sku_events_client=None):
        self.sku_events_client = sku_events_client or SkuEventsClient()

    @transaction.atomic
    def reserve(
        self,
        *,
        idempotency_key,
        items,
    ):
        operation = ReserveOperation.objects.filter(
            idempotency_key=idempotency_key,
        ).first()

        if operation is not None:
            return operation.result

        requested_by_uuid = self._collapse_items(items)
        locked_skus = self._lock_skus(requested_by_uuid)
        failed_items = self._get_reserve_failures(
            requested_by_uuid,
            locked_skus,
        )

        if failed_items:
            raise ReserveConflictError(failed_items=failed_items)

        response_items = []
        out_of_stock_skus = []

        for sku_uuid, quantity in requested_by_uuid.items():
            sku = locked_skus[sku_uuid]

            sku.active_quantity -= quantity
            sku.reserved_quantity += quantity
            sku.save(
                update_fields=[
                    "active_quantity",
                    "reserved_quantity",
                    "updated_at",
                ]
            )

            response_items.append(
                {
                    "sku_id": str(sku.uuid),
                    "reserved_quantity": quantity,
                    "remaining_stock": sku.active_quantity,
                }
            )

            if sku.active_quantity == 0:
                out_of_stock_skus.append(sku)

        result = {
            "reserved": True,
            "items": response_items,
        }

        ReserveOperation.objects.create(
            idempotency_key=idempotency_key,
            result=result,
        )

        transaction.on_commit(lambda: self._emit_out_of_stock_events(out_of_stock_skus))

        return result

    @transaction.atomic
    def unreserve(
        self,
        *,
        order_id,
        items,
    ):
        operation = UnreserveOperation.objects.filter(
            order_id=order_id,
        ).first()

        if operation is not None:
            return operation.result

        requested_by_uuid = self._collapse_items(items)
        locked_skus = self._lock_skus(requested_by_uuid)
        failed_items = self._get_unreserve_failures(
            requested_by_uuid,
            locked_skus,
        )

        if failed_items:
            raise UnreserveConflictError(failed_items=failed_items)

        for sku_uuid, quantity in requested_by_uuid.items():
            sku = locked_skus[sku_uuid]
            sku.active_quantity += quantity
            sku.reserved_quantity -= quantity
            sku.save(
                update_fields=[
                    "active_quantity",
                    "reserved_quantity",
                    "updated_at",
                ]
            )

        result = {
            "ok": True,
        }

        UnreserveOperation.objects.create(
            order_id=order_id,
            result=result,
        )

        return result

    def _collapse_items(self, items):
        requested_by_uuid = {}

        for item in items:
            sku_uuid = item["sku_id"]
            requested_by_uuid[sku_uuid] = (
                requested_by_uuid.get(sku_uuid, 0) + item["quantity"]
            )

        return requested_by_uuid

    def _lock_skus(self, requested_by_uuid):
        skus = (
            Sku.objects.select_for_update()
            .select_related("product")
            .filter(uuid__in=requested_by_uuid.keys())
        )

        return {sku.uuid: sku for sku in skus}

    def _get_reserve_failures(
        self,
        requested_by_uuid,
        locked_skus,
    ):
        failed_items = []

        for sku_uuid, quantity in requested_by_uuid.items():
            sku = locked_skus.get(sku_uuid)
            available = sku.active_quantity if sku is not None else 0

            if sku is None or available < quantity:
                failed_items.append(
                    {
                        "sku_id": str(sku_uuid),
                        "requested": quantity,
                        "available": available,
                        "reason": (
                            "OUT_OF_STOCK" if available == 0 else "INSUFFICIENT_STOCK"
                        ),
                    }
                )

        return failed_items

    def _get_unreserve_failures(
        self,
        requested_by_uuid,
        locked_skus,
    ):
        failed_items = []

        for sku_uuid, quantity in requested_by_uuid.items():
            sku = locked_skus.get(sku_uuid)
            reserved = sku.reserved_quantity if sku is not None else 0

            if sku is None or reserved < quantity:
                failed_items.append(
                    {
                        "sku_id": str(sku_uuid),
                        "requested": quantity,
                        "reserved": reserved,
                        "reason": "INSUFFICIENT_RESERVED",
                    }
                )

        return failed_items

    def _emit_out_of_stock_events(self, skus):
        for sku in skus:
            self.sku_events_client.emit_sku_out_of_stock(sku)
