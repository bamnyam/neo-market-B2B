import uuid

from django.db import models

from app.categories.models.categories import Category
from app.products.models.product_status import ProductStatus
from app.sellers.models.sellers import Seller


class Product(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    seller = models.ForeignKey(
        Seller, on_delete=models.PROTECT, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
    )
    description = models.TextField()
    status = models.CharField(
        max_length=50, choices=ProductStatus.choices, default=ProductStatus.CREATED
    )
    deleted = models.BooleanField(default=False)
    blocking_reason_id = models.UUIDField(
        null=True,
        blank=True,
    )
    blocking_reason_title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    moderator_comment = models.TextField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
