import uuid

from django.db import models

from app.invoices.models.invoice_status import InvoiceStatus
from app.sellers.models.sellers import Seller


class Invoice(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    seller = models.ForeignKey(
        Seller, on_delete=models.PROTECT, related_name="invoices"
    )
    status = models.CharField(
        max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
