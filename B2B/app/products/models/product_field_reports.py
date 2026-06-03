import uuid

from django.db import models

from app.products.models.products import Product
from app.skus.models.sku import Sku


class ProductFieldReport(models.Model):
    class FieldName(models.TextChoices):
        TITLE = "title", "Title"
        DESCRIPTION = "description", "Description"
        PRODUCT_IMAGES = "product_images", "Product images"
        CATEGORY = "category", "Category"
        SKU_NAME = "sku_name", "SKU name"
        SKU_IMAGE = "sku_image", "SKU image"
        SKU_PRICE = "sku_price", "SKU price"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="field_reports",
    )
    sku = models.ForeignKey(
        Sku,
        on_delete=models.CASCADE,
        related_name="field_reports",
        null=True,
        blank=True,
    )
    field_name = models.CharField(
        max_length=32,
        choices=FieldName.choices,
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
