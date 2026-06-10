import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


def forwards_status_values(apps, schema_editor):
    invoice_model = apps.get_model("invoices", "Invoice")
    status_mapping = {
        "created": "CREATED",
        "accepted": "ACCEPTED",
        "rejected": "CANCELLED",
    }

    for old_status, new_status in status_mapping.items():
        invoice_model.objects.filter(status=old_status).update(status=new_status)


def backwards_status_values(apps, schema_editor):
    invoice_model = apps.get_model("invoices", "Invoice")
    status_mapping = {
        "CREATED": "created",
        "ACCEPTED": "accepted",
        "CANCELLED": "rejected",
    }

    for old_status, new_status in status_mapping.items():
        invoice_model.objects.filter(status=old_status).update(status=new_status)


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0001_initial"),
        ("skus", "0005_reserveoperation_order_id"),
    ]

    operations = [
        migrations.RunPython(
            forwards_status_values,
            backwards_status_values,
        ),
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("PARTIALLY_ACCEPTED", "Partially accepted"),
                    ("ACCEPTED", "Accepted"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="CREATED",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="InvoiceItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                (
                    "accepted_quantity",
                    models.PositiveIntegerField(
                        default=0,
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="invoices.invoice",
                    ),
                ),
                (
                    "sku",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invoice_items",
                        to="skus.sku",
                    ),
                ),
            ],
        ),
    ]
