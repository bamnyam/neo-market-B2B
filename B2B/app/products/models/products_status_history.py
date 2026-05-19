import uuid

from django.db import models

from app.products.models.product_status import ProductStatus
from app.products.models.products import Product


class ProductStatusHistory(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="status_history"
    )
    status_from = models.CharField(max_length=50, choices=ProductStatus.choices)
    status_to = models.CharField(max_length=50, choices=ProductStatus.choices)
    changed_by = models.CharField(max_length=255)
    reason = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True)
