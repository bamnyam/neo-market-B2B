from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission


class IsSellerAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user is not None and not isinstance(
            request.user,
            AnonymousUser,
        )
