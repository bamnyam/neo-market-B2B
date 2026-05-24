from django.db import models


class ProductStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    ON_MODERATION = "ON_MODERATION", "On moderation"
    MODERATED = "MODERATED", "Moderated"
    BLOCKED = "BLOCKED", "Blocked"
    HARD_BLOCKED = "HARD_BLOCKED", "Hard blocked"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    ARCHIVED = "ARCHIVED", "Archived"
