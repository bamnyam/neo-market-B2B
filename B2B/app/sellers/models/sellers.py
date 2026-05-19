import re
import uuid

from django.core.validators import RegexValidator
from django.db import models

PHONE_RE = re.compile(r"^(?:\+7|8)?\d{10}$")
INN_RE = r"^(\d{10}|\d{12})$"


class Seller(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    company_name = models.CharField(max_length=200)
    inn = models.CharField(
        validators=[
            RegexValidator(
                regex=INN_RE,
                message="INN must contain 10 or 12 digits",
            )
        ],
        max_length=12,
        unique=True,
    )
    contact_email = models.EmailField(
        max_length=200,
        unique=True,
    )
    contact_phone = models.CharField(
        validators=[
            RegexValidator(
                regex=PHONE_RE,
                message="Phone number must be entered in the format: +70000000000",
            )
        ],
        max_length=20,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
