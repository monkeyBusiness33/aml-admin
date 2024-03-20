from rest_framework import serializers
from organisation.models.organisation import Organisation
from .airport import AirportDetailsSerializer
from .organisation import OrganisationDetailsSimpleSerializer


class HandlingLocationSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSimpleSerializer()
    airport_details = AirportDetailsSerializer()

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'airport_details', 'tiny_repr', 'short_repr', 'full_repr', 'is_lat_lon_available', ]
