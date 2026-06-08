import uuid

from django.db import models


class ProcessedModerationEvent(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    sender_service = models.CharField(max_length=64)
    idempotency_key = models.UUIDField(db_index=True)
    product_id = models.UUIDField()
    status = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sender_service", "idempotency_key"],
                name="unique_processed_moderation_event",
            )
        ]
