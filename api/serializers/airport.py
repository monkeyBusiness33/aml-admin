from rest_framework import serializers
from organisation.models.airport import AirportDetails
from organisation.models.organisation import Organisation
from .organisation import OrganisationDetailsSimpleSerializer


class AirportDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AirportDetails
        fields = ['icao_code', 'iata_code', ]


class AirportSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSimpleSerializer()
    airport_details = AirportDetailsSerializer()

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'airport_details', 'tiny_repr', 'short_repr', 'full_repr', ]
