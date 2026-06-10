from django.urls import path

from app.invoices.api.controller import InvoicesController


urlpatterns = [
    path("invoices", InvoicesController.as_view(), name="create-invoice"),
]
