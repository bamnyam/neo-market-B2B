import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from app.sellers.models import Seller
from django.conf import settings


class SellerJWTAuthentication(BaseAuthentication):
    AUTH_HEADER_PREFIX = "Bearer "
    SELLER_ID_CLAIM = "seller_id"
    ALGORITHM = "HS256"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise AuthenticationFailed("Invalid authorization header")

        if not auth_header.startswith(self.AUTH_HEADER_PREFIX):
            raise AuthenticationFailed("Invalid authorization header")

        token = auth_header.removeprefix(self.AUTH_HEADER_PREFIX).strip()
        payload = self._decode_token(token)
        seller = self._get_seller_from_payload(payload)

        return seller, payload

    def _decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[self.ALGORITHM])
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed("Invalid token") from exc

    def _get_seller_from_payload(self, payload: dict) -> Seller:
        seller_id = payload.get(self.SELLER_ID_CLAIM)
        if not seller_id:
            raise AuthenticationFailed("seller_id claim is required")

        try:
            return Seller.objects.get(id=seller_id)
        except Seller.DoesNotExist as exc:
            raise AuthenticationFailed("Seller not found") from exc
