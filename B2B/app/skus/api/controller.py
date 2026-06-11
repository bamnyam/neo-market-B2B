from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.common.authentication import B2CServiceAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.skus.api.serializers import (
    FulfillRequestSerializer,
    ReserveRequestSerializer,
    SkuCreateSerializer,
    SkuResponseSerializer,
    SkuUpdateSerializer,
    UnreserveRequestSerializer,
)
from app.skus.errors.sku_create_error import SkuCreateError
from app.skus.errors.sku_update_error import SkuUpdateError
from app.skus.services.reserve_service import (
    FulfillConflictError,
    ReserveConflictError,
    ReserveService,
    UnreserveConflictError,
)
from app.skus.services.sku_create_service import SkuCreateService
from app.skus.services.sku_update_service import SkuUpdateService


class SkusController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsSellerAuthenticated]

    create_service_class = SkuCreateService
    update_service_class = SkuUpdateService

    def post(self, request):
        serializer = SkuCreateSerializer(data=request.data)

        if not serializer.is_valid():
            field, errors = next(iter(serializer.errors.items()))
            message = errors[0] if isinstance(errors, list) else errors

            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": str(message),
                    "details": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

        return Response(
            self._serialize_sku(result.sku),
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, id):
        serializer = SkuUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid SKU request",
                    "details": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = self.update_service_class().update_sku(
                sku_uuid=id,
                seller=request.user,
                data=serializer.validated_data,
            )
        except SkuUpdateError as error:
            return Response(
                {
                    "code": error.code,
                    "message": error.message,
                },
                status=error.status_code,
            )

        return Response(
            self._serialize_sku(result.sku),
            status=status.HTTP_200_OK,
        )

    patch = put

    def _serialize_sku(self, sku):
        sku = (
            sku.__class__.objects.select_related("product")
            .prefetch_related("images", "characteristics")
            .get(id=sku.id)
        )

        return SkuResponseSerializer(
            {
                "id": sku.uuid,
                "product_id": sku.product.uuid,
                "name": sku.name,
                "price": int(sku.price),
                "cost_price": (
                    int(sku.cost_price) if sku.cost_price is not None else None
                ),
                "discount": int(sku.discount),
                "stock_quantity": sku.stock_quantity,
                "active_quantity": sku.active_quantity,
                "reserved_quantity": sku.reserved_quantity,
                "article": sku.article,
                "created_at": sku.created_at,
                "updated_at": sku.updated_at,
                "images": [
                    {
                        "id": image.uuid,
                        "url": image.url,
                        "ordering": image.ordering,
                    }
                    for image in sku.images.all()
                ],
                "characteristics": [
                    {
                        "id": characteristic.uuid,
                        "name": characteristic.name,
                        "value": characteristic.value,
                    }
                    for characteristic in sku.characteristics.all()
                ],
            }
        ).data


class ReserveController(APIView):
    authentication_classes = [B2CServiceAuthentication]
    permission_classes = [IsSellerAuthenticated]

    service_class = ReserveService

    def post(self, request):
        serializer = ReserveRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid reserve request",
                    "details": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = self.service_class().reserve(
                idempotency_key=serializer.validated_data["idempotency_key"],
                order_id=serializer.validated_data["order_id"],
                items=serializer.validated_data["items"],
            )
        except ReserveConflictError as error:
            return Response(
                {
                    "code": "CONFLICT",
                    "message": "Unable to reserve inventory",
                    "details": {
                        "failed_items": error.failed_items,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class UnreserveController(APIView):
    authentication_classes = [B2CServiceAuthentication]
    permission_classes = [IsSellerAuthenticated]

    service_class = ReserveService

    def post(self, request):
        serializer = UnreserveRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid unreserve request",
                    "details": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = self.service_class().unreserve(
                order_id=serializer.validated_data["order_id"],
                items=serializer.validated_data["items"],
            )
        except UnreserveConflictError as error:
            return Response(
                {
                    "code": "CONFLICT",
                    "message": "Unable to unreserve inventory",
                    "details": {
                        "failed_items": error.failed_items,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class FulfillController(APIView):
    authentication_classes = [B2CServiceAuthentication]
    permission_classes = [IsSellerAuthenticated]

    service_class = ReserveService

    def post(self, request):
        serializer = FulfillRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid fulfill request",
                    "details": serializer.errors,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = self.service_class().fulfill(
                order_id=serializer.validated_data["order_id"],
                items=serializer.validated_data["items"],
            )
        except FulfillConflictError as error:
            return Response(
                {
                    "code": "CONFLICT",
                    "message": "Unable to fulfill inventory",
                    "details": {
                        "failed_items": error.failed_items,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
