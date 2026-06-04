# Generated for US-B2B-08 OpenAPI alignment

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skus", "0004_reserve_operations"),
    ]

    operations = [
        migrations.AddField(
            model_name="reserveoperation",
            name="order_id",
            field=models.UUIDField(default=uuid.uuid4),
            preserve_default=False,
        ),
    ]
