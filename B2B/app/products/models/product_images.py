from django.db import models

from app.products.models.products import Product


class ProductImages(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    url = models.URLField(max_length=255)
    ordering = models.PositiveBigIntegerField()
