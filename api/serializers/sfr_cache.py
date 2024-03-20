from rest_framework import serializers

from handling.models import HandlingRequest, HandlingRequestFuelBooking


class HandlingRequestsFuelBookingOfflineCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestFuelBooking
        fields = ['fuel_release', ]


class HandlingRequestsOfflineCacheSerializer(serializers.ModelSerializer):
    fuel_booking = HandlingRequestsFuelBookingOfflineCacheSerializer(many=False)

    class Meta:
        model = HandlingRequest
        fields = ['id', 'fuel_booking', ]
