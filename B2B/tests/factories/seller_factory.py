import factory

from app.sellers.models import Seller


class SellerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Seller

    company_name = factory.Sequence(lambda n: f"Test seller {n}")
    inn = factory.Sequence(lambda n: f"{1000000000 + n}")
    contact_email = factory.Sequence(lambda n: f"seller{n}@test.com")
    contact_phone = factory.Sequence(lambda n: f"+79999999{n:03}")
