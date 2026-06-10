from dataclasses import dataclass

from django.db import transaction
from rest_framework import status

from app.invoices.errors import InvoiceCreateError
from app.invoices.models import Invoice, InvoiceItem
from app.products.models import ProductStatus
from app.skus.models import Sku


@dataclass(frozen=True)
class InvoiceCreateResult:
    invoice: Invoice


class InvoiceCreateService:
    @transaction.atomic
    def create_invoice(self, seller, items):
        sku_by_uuid = {
            sku.uuid: sku
            for sku in Sku.objects.select_related("product", "product__seller").filter(
                uuid__in=[item["sku_id"] for item in items],
            )
        }

        invoice_items = []

        for item in items:
            sku = sku_by_uuid.get(item["sku_id"])

            if sku is None:
                raise InvoiceCreateError(
                    code="NOT_FOUND",
                    message="SKU not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if sku.product.seller_id != seller.id:
                raise InvoiceCreateError(
                    code="NOT_OWNER",
                    message="One or more SKUs do not belong to the authenticated seller",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            if sku.product.status != ProductStatus.MODERATED:
                raise InvoiceCreateError(
                    code="INVALID_REQUEST",
                    message="Invoice can only be created for MODERATED products",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            invoice_items.append((sku, item["quantity"]))

        invoice = Invoice.objects.create(seller=seller)

        InvoiceItem.objects.bulk_create(
            [
                InvoiceItem(
                    invoice=invoice,
                    sku=sku,
                    quantity=quantity,
                )
                for sku, quantity in invoice_items
            ]
        )

        return InvoiceCreateResult(invoice=invoice)
