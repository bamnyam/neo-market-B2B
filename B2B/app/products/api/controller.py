from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductListItemSerializer,
    ProductResponseSerializer,
    ProductUpdateSerializer,
)
from app.products.errors.product_delete_error import ProductDeleteError
from app.products.models import Product
from app.products.services.product_delete_service import (
    ProductDeleteService,
)
from app.products.services.product_update_service import ProductUpdateService


class ProductsController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsSellerAuthenticated]

    delete_service_class = ProductDeleteService
    update_service_class = ProductUpdateService

    def post(self, request):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={"seller": request.user},
        )

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

        product = serializer.save()

        return Response(
            ProductResponseSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
        status_filter = request.query_params.get("status")
        include_deleted = (
            request.query_params.get("include_deleted", "false").lower() == "true"
        )

        products = (
            Product.objects.filter(
                seller=request.user,
            )
            .select_related(
                "seller",
                "category",
            )
            .prefetch_related(
                "images",
                "skus",
            )
            .order_by("-created_at")
        )

        if not include_deleted:
            products = products.filter(
                deleted=False,
            )

        if status_filter:
            products = products.filter(
                status=status_filter,
            )

        total_count = products.count()

        products = products[offset : offset + limit]

        return Response(
            {
                "items": ProductListItemSerializer(
                    products,
                    many=True,
                ).data,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):

        try:
            self.delete_service_class().delete_product(
                product_uuid=id,
                seller=request.user,
            )

        except ProductDeleteError as error:
            return Response(
                {
                    "code": error.code,
                    "message": error.message,
                },
                status=error.status_code,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    def put(self, request, id):
        try:
            product = Product.objects.get(uuid=id)
        except Product.DoesNotExist:
            return Response(
                {
                    "code": "NOT_FOUND",
                    "message": "Product not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductUpdateSerializer(
            data=request.data,
            context={"product": product},
        )

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
            result = self.update_service_class().update_product(
                product_uuid=id,
                seller=request.user,
                data=serializer.validated_data,
            )
        except ProductDeleteError as error:
            return Response(
                {
                    "code": error.code,
                    "message": error.message,
                },
                status=error.status_code,
            )

        return Response(
            ProductResponseSerializer(result.product).data,
            status=status.HTTP_200_OK,
        )

    patch = put
