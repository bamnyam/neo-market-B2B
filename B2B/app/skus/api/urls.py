from django.urls import path

from app.skus.api.controller import SkusController


urlpatterns = [
    path(
        "skus",
        SkusController.as_view(),
        name="create-sku",
    ),
    path(
        "skus/<uuid:id>",
        SkusController.as_view(),
        name="sku-detail",
    ),
]
