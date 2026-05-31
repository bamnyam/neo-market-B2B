from rest_framework import serializers


class SkuCharacteristicCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    value = serializers.CharField(
        min_length=1,
        max_length=255,
    )


class SKUImageCreateSerializer(serializers.Serializer):
    url = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    ordering = serializers.IntegerField(
        required=False,
        default=0,
    )


class SkuCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    name = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    price = serializers.IntegerField(
        min_value=0,
    )

    cost_price = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )

    discount = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    article = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    images = SKUImageCreateSerializer(
        many=True,
        required=False,
        default=list,
    )

    characteristics = SkuCharacteristicCreateSerializer(
        many=True,
        required=False,
        default=list,
    )


class SkuUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        min_length=1,
        max_length=255,
        required=False,
    )

    price = serializers.IntegerField(
        min_value=0,
        required=False,
    )

    cost_price = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )

    discount = serializers.IntegerField(
        min_value=0,
        required=False,
    )

    article = serializers.CharField(
        min_length=1,
        max_length=255,
        required=False,
    )

    image = serializers.CharField(
        min_length=1,
        max_length=255,
        required=False,
    )

    images = SKUImageCreateSerializer(
        many=True,
        required=False,
    )

    characteristics = SkuCharacteristicCreateSerializer(
        many=True,
        required=False,
    )


class SkuCharacteristicResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    value = serializers.CharField()


class SKUImageResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    url = serializers.CharField()
    ordering = serializers.IntegerField()


class SkuResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    product_id = serializers.UUIDField()

    name = serializers.CharField()

    price = serializers.IntegerField()
    cost_price = serializers.IntegerField(
        allow_null=True,
        required=False,
    )

    discount = serializers.IntegerField()

    stock_quantity = serializers.IntegerField()
    active_quantity = serializers.IntegerField()
    reserved_quantity = serializers.IntegerField()

    article = serializers.CharField()

    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    images = SKUImageResponseSerializer(
        many=True,
    )

    characteristics = SkuCharacteristicResponseSerializer(
        many=True,
    )
