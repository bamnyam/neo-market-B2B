from django.db import models

from app.categories.models.categories import Category
from app.products.models.product_status import ProductStatus
from app.sellers.models.sellers import Seller


class Product(models.Model):
    seller = models.ForeignKey(
        Seller, on_delete=models.PROTECT, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=50, choices=ProductStatus.choices, default=ProductStatus.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
