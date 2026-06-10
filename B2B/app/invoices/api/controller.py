from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.invoices.api.serializers import (
    InvoiceCreateSerializer,
    InvoiceResponseSerializer,
)
from app.invoices.errors import InvoiceCreateError
from app.invoices.services import InvoiceCreateService


class InvoicesController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsSellerAuthenticated]

    create_service_class = InvoiceCreateService

    def post(self, request):
        serializer = InvoiceCreateSerializer(data=request.data)

        if not serializer.is_valid():
            field, errors = next(iter(serializer.errors.items()))
            message = errors[0] if isinstance(errors, list) else errors

            return Response(
                {
                    "code": "INVALID_REQUEST",
                    "message": str(message),
                    "field": field,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self.create_service_class().create_invoice(
                seller=request.user,
                items=serializer.validated_data["items"],
            )
        except InvoiceCreateError as error:
            return Response(
                {
                    "code": error.code,
                    "message": error.message,
                },
                status=error.status_code,
            )

        invoice = (
            result.invoice.__class__.objects.select_related("seller")
            .prefetch_related("items__sku")
            .get(id=result.invoice.id)
        )

        return Response(
            InvoiceResponseSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )
