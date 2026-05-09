from django.db import models


class InvoiceStatus(models.TextChoices):
    CREATED = "created", "Created"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
