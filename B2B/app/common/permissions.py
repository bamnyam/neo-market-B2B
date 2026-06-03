from rest_framework.permissions import BasePermission


class IsSellerAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "access_mode", None) in {
            "seller",
            "moderation_service",
            "catalog_service",
        }
