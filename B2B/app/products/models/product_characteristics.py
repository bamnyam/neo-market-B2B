from django.db import models

from app.products.models.products import Product


class ProductCharacteristics(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="characteristics"
    )
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
