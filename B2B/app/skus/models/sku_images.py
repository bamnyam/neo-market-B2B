# app/skus/models/sku_images.py

import uuid

from django.db import models

from app.skus.models.sku import Sku


class SkuImages(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    sku = models.ForeignKey(
        Sku,
        on_delete=models.CASCADE,
        related_name="images",
    )

    url = models.CharField(max_length=255)

    ordering = models.IntegerField(default=0)
