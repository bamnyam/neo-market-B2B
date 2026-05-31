import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ModerationEventsClient:
    def emit_product_created(self, product):
        self._emit_event(
            product=product,
            event_type="CREATED",
        )

    def emit_product_updated(self, product):
        self._emit_event(
            product=product,
            event_type="EDITED",
        )

    def emit_product_edited(self, product):
        self._emit_event(
            product=product,
            event_type="EDITED",
        )

    def _emit_event(
        self,
        *,
        product,
        event_type,
    ):
        payload = {
            "idempotency_key": self._build_idempotency_key(
                product.uuid,
                event_type,
            ),
            "product_id": str(product.uuid),
            "seller_id": str(product.seller.uuid),
            "event": event_type,
            "date": timezone.now().isoformat().replace("+00:00", "Z"),
        }

        try:
            requests.post(
                f"{settings.MODERATION_URL}/api/v1/events/product",
                json=payload,
                headers={
                    "X-Service-Key": settings.B2B_TO_MOD_KEY,
                },
                timeout=3,
            )
        except requests.RequestException:
            logger.exception(
                "Failed to emit product %s event to moderation",
                event_type,
            )

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
