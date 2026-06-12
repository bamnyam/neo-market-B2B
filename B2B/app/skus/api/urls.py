from django.urls import path

from app.skus.api.controller import (
    FulfillController,
    ReserveController,
    SkusController,
    UnreserveController,
)


urlpatterns = [
    path(
        "inventory/fulfill",
        FulfillController.as_view(),
        name="fulfill-sku",
    ),
    path(
        "inventory/reserve",
        ReserveController.as_view(),
        name="reserve-sku",
    ),
    path(
        "inventory/unreserve",
        UnreserveController.as_view(),
        name="unreserve-sku",
    ),
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
