from rest_framework import serializers

from api.serializers.user import PersonSerializer, PersonRoleSerializer
from organisation.models import *


class OrganisationTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganisationType
        fields = ['id', 'name', ]


class OrganisationDetailsSerializer(serializers.ModelSerializer):
    type = OrganisationTypeSerializer()

    class Meta:
        model = OrganisationDetails
        fields = ['registered_name', 'trading_name', 'type', ]


class OrganisationDetailsSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganisationDetails
        fields = ['registered_name', 'trading_name', ]


class OrganisationLogoMottoSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganisationLogoMotto
        fields = ['logo', 'motto', ]


class OrganisationSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSerializer()
    full_repr = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = ['id', 'tiny_repr', 'short_repr', 'full_repr', 'details', ]

    def get_full_repr(self, obj):
        return obj.full_repr


class HandlerOrganisationSerializer(OrganisationSerializer):
    is_email_addresses_available = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = ['id', 'full_repr', 'is_email_addresses_available', 'details', ]

    def get_is_email_addresses_available(self, obj):
        handler_emails = obj.get_email_address()
        return bool(handler_emails)


class OrganisationWithLogoSerializer(serializers.ModelSerializer):
    '''
    Serializer for the auth endpoint to display user's organisation details
    '''
    details = OrganisationDetailsSerializer()
    logo_motto = OrganisationLogoMottoSerializer()

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'logo_motto', ]


class OrganisationPeopleSerializer(serializers.ModelSerializer):
    person = PersonSerializer()
    role = PersonRoleSerializer()

    class Meta:
        model = OrganisationPeople
        fields = ['id', 'person', 'role', 'job_title', ]
