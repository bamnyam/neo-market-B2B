import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from app.sellers.models import Seller


class SellerJWTAuthentication(BaseAuthentication):
    AUTH_HEADER_PREFIX = "Bearer "
    SELLER_ID_CLAIM = "seller_id"
    ALGORITHM = "HS256"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        if not auth_header.startswith(self.AUTH_HEADER_PREFIX):
            raise AuthenticationFailed("Invalid authorization header")

        token = auth_header.removeprefix(self.AUTH_HEADER_PREFIX).strip()
        payload = self._decode_token(token)
        seller = self._get_seller_from_payload(payload)

        return seller, payload

    def authenticate_header(self, request):
        return "Bearer"

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


class ServicePrincipal:
    def __init__(self, name: str):
        self.name = name

    @property
    def is_authenticated(self):
        return True


class SellerOrModerationAuthentication(SellerJWTAuthentication):
    SERVICE_KEY_HEADER = "X-Service-Key"

    def authenticate(self, request):
        service_key = request.headers.get(self.SERVICE_KEY_HEADER)

        if service_key:
            if service_key != settings.B2B_TO_MOD_KEY:
                raise AuthenticationFailed("Invalid service key")

            request.access_mode = "moderation_service"
            return ServicePrincipal("moderation"), {"service": "moderation"}

        result = super().authenticate(request)

        if result is not None:
            request.access_mode = "seller"

        return result


class B2CServiceAuthentication(BaseAuthentication):
    SERVICE_KEY_HEADER = "X-Service-Key"

    def authenticate(self, request):
        service_key = request.headers.get(self.SERVICE_KEY_HEADER)

        if not service_key:
            return None

        if service_key != settings.B2B_TO_B2C_KEY:
            raise AuthenticationFailed("Invalid service key")

        return ServicePrincipal("b2c"), {"service": "b2c"}
