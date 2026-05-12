from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.common.authentication import SellerJWTAuthentication
from app.products.api.serializers import ProductCreateSerializer, ProductResponseSerializer


class ProductsController(APIView):
    authentication_classes = [SellerJWTAuthentication]
    permission_classes = [IsAuthenticated]

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