from django.db import models


class InvoiceStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED", "Partially accepted"
    ACCEPTED = "ACCEPTED", "Accepted"
    CANCELLED = "CANCELLED", "Cancelled"
