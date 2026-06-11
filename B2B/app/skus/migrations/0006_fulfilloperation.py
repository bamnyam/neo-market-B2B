from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skus", "0005_reserveoperation_order_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="FulfillOperation",
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
                "db_table": "fulfill_operations",
            },
        ),
    ]
