from django.urls import path

from app.products.api.controller import ProductsController

urlpatterns = [
    path("products", ProductsController.as_view(), name="create-product"),
]