from django.db import models


class ProductStatus(models.TextChoices):
    CREATED = "created", "Created"
    DRAFT = "draft", "Draft"
    MODERATION = "moderation", "Moderation"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"
