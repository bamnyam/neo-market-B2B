import uuid

from django.db.models import Min, Prefetch, Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerOrModerationAuthentication
from app.common.permissions import IsSellerAuthenticated
from app.products.api.serializers import (
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListItemSerializer,
    ModerationEventSerializer,
    ProductPublicDetailSerializer,
    ProductPublicListItemSerializer,
    ProductResponseSerializer,
    ProductUpdateSerializer,
)
from app.products.errors.product_delete_error import ProductDeleteError
from app.products.models import Product, ProductStatus
from app.products.services.moderation_event_service import ModerationEventService
from app.products.services.product_delete_service import (
    ProductDeleteService,
)
from app.products.services.product_update_service import ProductUpdateService
from app.skus.models import Sku


class ProductsController(APIView):
    authentication_classes = [SellerOrModerationAuthentication]
    permission_classes = [IsSellerAuthenticated]

    invalid_uuid = object()

    delete_service_class = ProductDeleteService
    update_service_class = ProductUpdateService

    def post(self, request):
        self._require_seller_access(request)

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

        if getattr(request, "access_mode", None) == "catalog_service":
            return self._get_catalog(request)

        pagination = self._parse_pagination(request)

        if isinstance(pagination, Response):
            return pagination

        limit, offset = pagination
        status_filter = request.query_params.get("status")
        search_filter = request.query_params.get("search")
        include_deleted = self._parse_bool(
            request.query_params.get("include_deleted", "false")
        )

        if include_deleted is None:
            return self._invalid_query_param(
                "include_deleted",
                "include_deleted must be true or false",
            )

        if status_filter and status_filter not in ProductStatus.values:
            return self._invalid_query_param(
                "status",
                "status must be a valid ProductStatus",
            )

        for owner_param in ("seller_id", "user_id", "owner_id"):
            if owner_param in request.query_params:
                return self._invalid_query_param(
                    owner_param,
                    f"{owner_param} is not allowed",
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

        if search_filter:
            products = products.filter(title__icontains=search_filter)

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

        access_mode = getattr(request, "access_mode", "seller")
        products = self._products_with_detail_relations().filter(uuid=product_uuid)

        if access_mode == "seller":
            products = products.filter(seller=request.user)
        elif access_mode == "catalog_service":
            products = self._filter_visible_catalog(products)

        product = products.first()

        if product is None:
            return Response(
                {
                    "code": "NOT_FOUND",
                    "message": "Product not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer_class = (
            ProductPublicDetailSerializer
            if access_mode == "catalog_service"
            else ProductDetailSerializer
        )

        return Response(serializer_class(product).data, status=status.HTTP_200_OK)

    def delete(self, request, id):
        self._require_seller_access(request)

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
        self._require_seller_access(request)

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

    def _get_catalog(self, request):
        pagination = self._parse_pagination(request)

        if isinstance(pagination, Response):
            return pagination

        limit, offset = pagination
        ids = self._parse_ids_param(request.query_params.get("ids"))
        category = self._parse_optional_uuid(
            request.query_params.get("category")
            or request.query_params.get("category_id")
        )
        search_filter = request.query_params.get("search")
        sort = request.query_params.get("sort", "date_desc")

        if ids is None:
            return Response(
                {
                    "code": "INVALID_REQUEST",
                    "message": "ids must be a comma-separated list of UUIDs",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if category is self.invalid_uuid:
            return self._invalid_query_param(
                "category",
                "category must be a valid UUID",
            )

        if sort not in {"price_asc", "price_desc", "date_desc"}:
            return self._invalid_query_param(
                "sort",
                "sort must be one of price_asc, price_desc, date_desc",
            )

        products = self._filter_visible_catalog(
            Product.objects.select_related("seller", "category")
            .prefetch_related(
                "images",
                Prefetch(
                    "skus",
                    queryset=Sku.objects.filter(active_quantity__gt=0),
                ),
            )
        )

        if ids:
            products = products.filter(uuid__in=ids)

        if category is not None:
            products = products.filter(category__uuid=category)

        if search_filter:
            products = products.filter(
                Q(title__icontains=search_filter)
                | Q(description__icontains=search_filter)
            )

        products = self._sort_catalog(products, sort)

        total_count = products.count()
        products = products[offset : offset + limit]

        return Response(
            {
                "items": ProductPublicListItemSerializer(
                    products,
                    many=True,
                ).data,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            },
            status=status.HTTP_200_OK,
        )

    def _filter_visible_catalog(self, products):
        return products.filter(
            status=ProductStatus.MODERATED,
            deleted=False,
            skus__active_quantity__gt=0,
        ).distinct()

    def _products_with_detail_relations(self):
        return Product.objects.select_related("seller", "category").prefetch_related(
            "images",
            "characteristics",
            Prefetch(
                "skus",
                queryset=Sku.objects.prefetch_related("images", "characteristics"),
            ),
            "field_reports__sku",
        )

    def _parse_ids_param(self, value):
        if not value:
            return []

        try:
            return [
                uuid.UUID(raw_id.strip())
                for raw_id in value.split(",")
                if raw_id.strip()
            ]
        except ValueError:
            return None

    def _parse_optional_uuid(self, value):
        if not value:
            return None

        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return self.invalid_uuid

    def _parse_pagination(self, request):
        try:
            limit = int(request.query_params.get("limit", 20))
            offset = int(request.query_params.get("offset", 0))
        except (TypeError, ValueError):
            return self._invalid_query_param(
                "pagination",
                "limit and offset must be integers",
            )

        if limit < 1 or limit > 100:
            return self._invalid_query_param(
                "limit",
                "limit must be between 1 and 100",
            )

        if offset < 0:
            return self._invalid_query_param(
                "offset",
                "offset must be greater than or equal to 0",
            )

        return limit, offset

    def _parse_bool(self, value):
        normalized = str(value).lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

        return None

    def _sort_catalog(self, products, sort):
        if sort == "price_asc":
            return products.annotate(
                min_visible_price=Min(
                    "skus__price",
                    filter=Q(skus__active_quantity__gt=0),
                )
            ).order_by("min_visible_price", "-created_at")

        if sort == "price_desc":
            return products.annotate(
                min_visible_price=Min(
                    "skus__price",
                    filter=Q(skus__active_quantity__gt=0),
                )
            ).order_by("-min_visible_price", "-created_at")

        return products.order_by("-created_at")

    def _invalid_query_param(self, field, message):
        return Response(
            {
                "code": "INVALID_REQUEST",
                "message": message,
                "field": field,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _require_seller_access(self, request):
        if getattr(request, "access_mode", None) != "seller":
            raise PermissionDenied("Seller authorization required")


class ModerationEventsController(APIView):
    authentication_classes = [SellerOrModerationAuthentication]
    permission_classes = [IsSellerAuthenticated]

    service_class = ModerationEventService

    def post(self, request):
        if getattr(request, "access_mode", None) != "moderation_service":
            raise PermissionDenied("Moderation service authorization required")

        serializer = ModerationEventSerializer(data=request.data)

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
            self.service_class().apply(
                {
                    **serializer.validated_data,
                    "sender_service": request.user.name,
                }
            )
        except Product.DoesNotExist:
            return Response(
                {
                    "code": "NOT_FOUND",
                    "message": "Product not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
