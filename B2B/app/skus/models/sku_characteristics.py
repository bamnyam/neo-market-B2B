from django.db import models

from app.skus.models.sku import Sku


class SkuCharacteristics(models.Model):
    sku = models.ForeignKey(Sku, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
