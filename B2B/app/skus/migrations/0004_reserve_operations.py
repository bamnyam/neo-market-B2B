# Generated for US-B2B-08

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skus", "0003_skucharacteristics_uuid"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReserveOperation",
            fields=[
                (
                    "idempotency_key",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("result", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "reserve_operations",
            },
        ),
        migrations.CreateModel(
            name="UnreserveOperation",
            fields=[
                (
                    "order_id",
                    models.UUIDField(
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("result", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "unreserve_operations",
            },
        ),
    ]
