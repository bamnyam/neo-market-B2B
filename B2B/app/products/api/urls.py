from django.urls import path

from app.products.api.controller import ModerationEventsController, ProductsController

urlpatterns = [
    path(
        "events/moderation",
        ModerationEventsController.as_view(),
        name="moderation-events",
    ),
    path(
        "moderation/events",
        ModerationEventsController.as_view(),
        name="moderation-events-openapi-alias",
    ),
    path("products", ProductsController.as_view(), name="create-product"),
    path(
        "products/<str:id>",
        ProductsController.as_view(),
        name="product-delete",
    ),
]
