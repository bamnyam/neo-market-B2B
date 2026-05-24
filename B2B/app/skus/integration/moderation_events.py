import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ModerationEventsClient:
    def emit_product_created(self, product):
        event_date = timezone.now().isoformat().replace("+00:00", "Z")

        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "product_id": str(product.uuid),
            "seller_id": str(product.seller.uuid),
            "event": "CREATED",
            "date": event_date,
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
            logger.exception("Failed to emit product CREATED event to moderation")
