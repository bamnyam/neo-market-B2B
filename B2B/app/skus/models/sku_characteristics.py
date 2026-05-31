import uuid

from django.db import models

from app.skus.models.sku import Sku


class SkuCharacteristics(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    sku = models.ForeignKey(
        Sku,
        on_delete=models.CASCADE,
        related_name="characteristics",
    )
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
