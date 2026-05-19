import uuid

from django.db import models

from app.products.models.products import Product


class ProductImages(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    url = models.URLField(max_length=255)
    ordering = models.PositiveBigIntegerField()
