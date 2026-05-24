from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductListItemSerializer,
    ProductResponseSerializer,
)
from app.products.errors.product_delete_error import ProductDeleteError
from app.products.models import Product
from app.products.services.product_delete_service import (
    ProductDeleteService,
)


class ProductsController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsSellerAuthenticated]

    delete_service_class = ProductDeleteService

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
            {
                "ok": True,
            },
            status=status.HTTP_200_OK,
        )
