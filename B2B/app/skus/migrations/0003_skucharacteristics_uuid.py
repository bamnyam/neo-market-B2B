# Generated for US-B2B-03

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("skus", "0002_alter_skucharacteristics_sku_skuimages"),
    ]

    operations = [
        migrations.AddField(
            model_name="skucharacteristics",
            name="uuid",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
