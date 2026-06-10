from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("app.products.api.urls")),
    path("api/v1/", include("app.skus.api.urls")),
    path("api/v1/", include("app.invoices.api.urls")),
]
