from rest_framework import serializers
from organisation.models.operator import OperatorDetails
from organisation.models.organisation import Organisation
from .organisation import OrganisationDetailsSimpleSerializer


class OperatorDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = OperatorDetails
        fields = ['contact_email', 'contact_phone', ]


class OperatorSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSimpleSerializer()
    operator_details = OperatorDetailsSerializer()

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'operator_details', ]
