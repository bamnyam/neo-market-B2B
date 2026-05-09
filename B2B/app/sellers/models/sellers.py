import re

from django.core.validators import RegexValidator
from django.db import models

PHONE_RE = re.compile(r"^(?:\+7|8)?\d{10}$")
INN_RE = r"^(\d{10}|\d{12})$"


class Seller(models.Model):
    company_name = models.CharField(max_length=200)
    inn = RegexValidator(
        regex=PHONE_RE,
        message="Phone number must be entered in the format: +70000000000",
    )
    contact_email = models.EmailField(max_length=200)
    contact_phone = RegexValidator(
        regex=INN_RE, message="INN must contain 10 or 12 digits"
    )
    created_at = models.DateTimeField(auto_now_add=True)
