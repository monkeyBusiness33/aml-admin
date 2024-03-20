from rest_framework import serializers
from core.models import *


class UnitOfMeasurementSerializer(serializers.ModelSerializer):

    class Meta:
        model = UnitOfMeasurement
        fields = ['id', 'description', 'description_plural', 'code', ]


class AirCardPrefixSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField()

    class Meta:
        model = AirCardPrefix
        fields = ['id', 'number_prefix', 'is_active']


class AirCardPrefixSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = AirCardPrefix
        fields = ['id', 'number_prefix', ]
