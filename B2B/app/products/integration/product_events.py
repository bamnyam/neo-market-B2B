import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProductEventsClient:
    def emit_product_deleted(self, product):
        deleted_at = timezone.now().isoformat().replace("+00:00", "Z")

        self._safe_emit(
            self._emit_to_moderation,
            product,
            deleted_at,
        )

        self._safe_emit(
            self._emit_to_b2c,
            product,
            deleted_at,
        )

    def _safe_emit(self, func, product, deleted_at):
        try:
            func(product, deleted_at)
        except requests.RequestException:
            logger.exception("Failed to emit product deleted event")

    def _emit_to_moderation(self, product, deleted_at):
        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "product_id": str(product.uuid),
            "seller_id": str(product.seller.uuid),
            "event": "DELETED",
            "date": deleted_at,
        }

        requests.post(
            f"{settings.MODERATION_URL}/api/v1/events/product",
            json=payload,
            headers={
                "X-Service-Key": settings.B2B_TO_MOD_KEY,
            },
            timeout=3,
        )

    def _emit_to_b2c(self, product, deleted_at):
        sku_ids = [str(sku.uuid) for sku in product.skus.all()]

        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "event": "PRODUCT_DELETED",
            "product_id": str(product.uuid),
            "sku_ids": sku_ids,
            "date": deleted_at,
        }

        requests.post(
            f"{settings.B2C_URL}/api/v1/events/product",
            json=payload,
            headers={
                "X-Service-Key": settings.B2B_TO_B2C_KEY,
            },
            timeout=3,
        )
