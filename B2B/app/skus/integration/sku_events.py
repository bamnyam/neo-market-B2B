import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SkuEventsClient:
    def emit_sku_out_of_stock(self, sku):
        payload = {
            "idempotency_key": self._build_idempotency_key(
                sku.uuid,
                "SKU_OUT_OF_STOCK",
            ),
            "event": "SKU_OUT_OF_STOCK",
            "sku_id": str(sku.uuid),
            "product_id": str(sku.product.uuid),
            "date": timezone.now().isoformat().replace("+00:00", "Z"),
        }

        try:
            requests.post(
                f"{settings.B2C_URL}/api/v1/events/product",
                json=payload,
                headers={
                    "X-Service-Key": settings.B2B_TO_B2C_KEY,
                },
                timeout=3,
            )
        except requests.RequestException:
            logger.exception("Failed to emit SKU_OUT_OF_STOCK event to B2C")

    def _build_idempotency_key(
        self,
        sku_id,
        event_type,
    ):
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{sku_id}:{event_type}",
            )
        )
