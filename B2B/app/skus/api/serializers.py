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


class SkuCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    name = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    price = serializers.IntegerField(
        min_value=1,
    )

    cost_price = serializers.IntegerField(
        min_value=1,
    )

    discount = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    image = serializers.CharField(
        min_length=1,
        max_length=255,
    )

    characteristics = SkuCharacteristicCreateSerializer(
        many=True,
        required=False,
        default=list,
    )


class SkuCharacteristicResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    value = serializers.CharField()


class SkuResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    price = serializers.IntegerField()
    cost_price = serializers.IntegerField()
    discount = serializers.IntegerField()
    image = serializers.CharField()
    active_quantity = serializers.IntegerField()
    reserved_quantity = serializers.IntegerField()
    characteristics = SkuCharacteristicResponseSerializer(many=True)
