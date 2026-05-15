import factory

from app.sellers.models import Seller


class SellerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Seller

    company_name = "Test seller"
    inn = "1234567890"
    contact_email = "seller@test.com"
    contact_phone = "+79999999999"
