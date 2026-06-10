from rest_framework import serializers

from app.invoices.models import Invoice


class InvoiceItemCreateSerializer(serializers.Serializer):
    sku_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class InvoiceCreateSerializer(serializers.Serializer):
    items = InvoiceItemCreateSerializer(
        many=True,
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")

        return value


class InvoiceResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(
        source="uuid",
        read_only=True,
    )
    seller_id = serializers.UUIDField(
        source="seller.uuid",
        read_only=True,
    )
    items = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "seller_id",
            "status",
            "created_at",
            "updated_at",
            "accepted_at",
            "items",
        ]

    def get_items(self, obj):
        return [
            {
                "id": str(item.uuid),
                "sku_id": str(item.sku.uuid),
                "quantity": item.quantity,
                "accepted_quantity": item.accepted_quantity,
            }
            for item in obj.items.all()
        ]
