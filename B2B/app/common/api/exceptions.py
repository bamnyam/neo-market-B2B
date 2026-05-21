from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
)
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        response.data = {
            "code": "UNAUTHORIZED",
            "message": _get_error_message(exc),
        }
        return response

    if isinstance(exc, PermissionDenied):
        response.status_code = status.HTTP_403_FORBIDDEN
        response.data = {
            "code": "FORBIDDEN",
            "message": _get_error_message(exc),
        }
        return response

    if isinstance(exc, (NotFound, Http404)):
        response.status_code = status.HTTP_404_NOT_FOUND
        response.data = {
            "code": "NOT_FOUND",
            "message": _get_error_message(exc),
        }
        return response

    return response


def _get_error_message(exc):
    detail = getattr(exc, "detail", None)

    if isinstance(detail, list):
        return " ".join(str(item) for item in detail)

    if isinstance(detail, dict):
        return str(detail)

    if detail:
        return str(detail)

    return str(exc)
