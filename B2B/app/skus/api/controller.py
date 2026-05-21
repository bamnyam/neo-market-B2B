from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.skus.api.serializers import SkuCreateSerializer
from app.skus.errors.sku_create_error import SkuCreateError
from app.skus.services.sku_create_service import SkuCreateService


class SkusController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsSellerAuthenticated]

    create_service_class = SkuCreateService

    def post(self, request):
        serializer = SkuCreateSerializer(data=request.data)

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
            result = self.create_service_class().create_sku(
                seller=request.user,
                data=serializer.validated_data,
            )
        except SkuCreateError as error:
            return Response(
                {
                    "code": error.code,
                    "message": error.message,
                },
                status=error.status_code,
            )

        sku = result.sku
        image = sku.images.order_by("ordering").first()

        return Response(
            {
                "id": str(sku.uuid),
                "product_id": str(sku.product.uuid),
                "name": sku.name,
                "price": int(sku.price),
                "cost_price": int(sku.cost_price),
                "discount": int(sku.discount),
                "image": image.url if image else None,
                "active_quantity": sku.active_quantity,
                "reserved_quantity": sku.reserved_quantity,
                "characteristics": [
                    {
                        "id": str(characteristic.uuid),
                        "name": characteristic.name,
                        "value": characteristic.value,
                    }
                    for characteristic in sku.characteristics.all()
                ],
            },
            status=status.HTTP_201_CREATED,
        )
