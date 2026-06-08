import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class B2CProductEventsClient:
    def emit_product_blocked(self, product):
        sku_ids = [
            str(sku.uuid) for sku in product.skus.all() if sku.active_quantity > 0
        ]

        if not sku_ids:
            return

        payload = {
            "idempotency_key": self._build_idempotency_key(
                product.uuid,
                "PRODUCT_BLOCKED",
            ),
            "event": "PRODUCT_BLOCKED",
            "product_id": str(product.uuid),
            "sku_ids": sku_ids,
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
            logger.exception("Failed to emit product blocked event")

    def _build_idempotency_key(
        self,
        product_id,
        event_type,
    ):
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{product_id}:{event_type}",
            )
        )
