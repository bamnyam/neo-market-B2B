import uuid

from django.db import models


class Category(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
