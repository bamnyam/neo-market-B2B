import uuid
from django.db import models

from app.products.models.products import Product


class Sku(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="skus",
    )

    name = models.CharField(max_length=255)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    stock_quantity = models.IntegerField(default=0)

    active_quantity = models.IntegerField(default=0)

    reserved_quantity = models.IntegerField(default=0)

    article = models.CharField(
        max_length=255,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
