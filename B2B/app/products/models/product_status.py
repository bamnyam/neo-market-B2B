from django.db import models


class ProductStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    MODERATION = "MODERATION", "Moderation"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    ARCHIVED = "ARCHIVED", "Archived"
