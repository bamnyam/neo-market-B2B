from django.db import models

from app.products.models.products import Product


class Sku(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="skus",
    )
    name = models.CharField(max_length=255)
    price = models.PositiveIntegerField()
    stock_quantity = models.PositiveIntegerField()
    article = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
