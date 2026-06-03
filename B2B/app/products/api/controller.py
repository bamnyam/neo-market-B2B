import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerOrModerationAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductDetailSerializer,
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
    authentication_classes = [SellerOrModerationAuthentication]
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

    def get(self, request, id=None):
        if id is not None:
            return self._get_detail(request, id)

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

    def _get_detail(self, request, id):
        product_uuid = self._parse_product_uuid(id)

        if product_uuid is None:
            return Response(
                {
                    "code": "INVALID_REQUEST",
                    "message": "id must be a valid UUID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        products = (
            Product.objects.select_related("seller", "category")
            .prefetch_related(
                "images",
                "characteristics",
                "skus__images",
                "skus__characteristics",
                "field_reports__sku",
            )
            .filter(uuid=product_uuid)
        )

        if getattr(request, "access_mode", "seller") == "seller":
            products = products.filter(seller=request.user)

        product = products.first()

        if product is None:
            return Response(
                {
                    "code": "NOT_FOUND",
                    "message": "Product not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            ProductDetailSerializer(product).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        product_uuid = self._parse_product_uuid(id)

        if product_uuid is None:
            return Response(
                {
                    "code": "INVALID_REQUEST",
                    "message": "id must be a valid UUID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            self.delete_service_class().delete_product(
                product_uuid=product_uuid,
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
        product_uuid = self._parse_product_uuid(id)

        if product_uuid is None:
            return Response(
                {
                    "code": "INVALID_REQUEST",
                    "message": "id must be a valid UUID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(uuid=product_uuid)
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
                product_uuid=product_uuid,
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

    def _parse_product_uuid(self, value):
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return None
