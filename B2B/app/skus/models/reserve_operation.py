import uuid

from django.db import models


class ReserveOperation(models.Model):
    idempotency_key = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    result = models.JSONField()

    order_id = models.UUIDField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reserve_operations"


class UnreserveOperation(models.Model):
    order_id = models.UUIDField(
        primary_key=True,
        editable=False,
    )

    result = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unreserve_operations"
