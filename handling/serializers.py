from django.db import transaction
from django.db.models.aggregates import Count
from django.db.models.expressions import F, Case, When, Value
from django.db.models.fields import BooleanField, IntegerField
from django.db.models.query_utils import Q
from django.db.models.signals import post_save
from django.utils import timezone
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework.exceptions import NotFound

from api.serializers.handling_base import HandlingLocationSerializer
from api.serializers.organisation import OrganisationDetailsSimpleSerializer
from api.serializers.user import PersonSerializer
from api.utils.handling import handling_reqeust_create_service_booking
from api.utils.helpers import get_mobile_app_version
from core.models.aircard import AirCardPrefix
from core.utils.validators import aircard_number_validation_simple, aircard_expiration_validation
from handling.utils.client_notifications import handling_request_received_push_notification
from handling.utils.handling_request_func import handling_request_cancel_actions
from handling.utils.localtime import get_utc_from_airport_local_time
from organisation.models import HandlerDetails, Organisation
from user.models import Person
from api.serializers.airport import AirportSerializer
from api.serializers.aircraft import AircraftTypeSerializer
from api.serializers.core import UnitOfMeasurementSerializer
from django.db.models.functions import Coalesce

from .models import HandlingServiceAvailability, HandlingService, HandlingRequestServices, HandlingRequestMovement, \
    HandlingRequestType, HandlingRequestFuelBooking, HandlingRequestCrewMemberPosition, HandlingRequestCrew, \
    HandlingRequest, HandlingRequestAmendment, ServiceProvisionForm, ServiceProvisionFormServiceTaken, \
    HandlingRequestFeedback
from .utils.email_diff_generator import generate_diff_dict
from datetime import datetime, date

from .utils.validators import validate_handling_request_for_duplicate, validate_handling_request_for_duplicate_v2


class RelatedFieldAlternative(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        self.serializer = kwargs.pop('serializer', None)
        if self.serializer is not None and not issubclass(self.serializer, serializers.Serializer):
            raise TypeError('"serializer" is not a valid serializer class')

        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return False if self.serializer else True

    def to_representation(self, instance):
        if self.serializer:
            return self.serializer(instance, context=self.context).data
        return super().to_representation(instance)


class HandlingAgentDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlerDetails
        fields = ['contact_phone', 'contact_email', 'ops_phone', 'ops_email',
                  'ops_frequency', 'has_pax_lounge', 'has_crew_room', 'has_vip_lounge', ]


class HandlingAgentSerializer(serializers.ModelSerializer):
    handler_details = HandlingAgentDetailsSerializer(
        many=False, read_only=True)
    details = OrganisationDetailsSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'handler_details', ]


class HandlingServiceAvailabilitySerializer(serializers.Serializer):
    airport = serializers.IntegerField()
    direction = serializers.CharField()


class HandlingServiceBoolAvailabilitySerializer(serializers.Serializer):
    airport = serializers.IntegerField()
    arrival = serializers.BooleanField()
    departure = serializers.BooleanField()


class HandlingServiceSerializer(serializers.ModelSerializer):
    """
    Handling Service serializer returns all registered services with
    its applicable airports along with the direction.
    """
    is_dla = serializers.SerializerMethodField()
    is_dla_visible_arrival = serializers.SerializerMethodField()
    is_dla_visible_departure = serializers.SerializerMethodField()
    availability = HandlingServiceAvailabilitySerializer(source='get_availability', many=True)
    availability_bool = HandlingServiceBoolAvailabilitySerializer(source='get_availability_bool', many=True)
    is_passengers_handling = serializers.SerializerMethodField()
    quantity_selection_uom = UnitOfMeasurementSerializer()

    def get_is_passengers_handling(self, service):  # noqa
        return service.codename == 'passengers_handling'

    class Meta:
        model = HandlingService
        fields = ['id', 'name', 'codename',
                  'is_allowed_free_text', 'is_allowed_quantity_selection',
                  'quantity_selection_uom',

                  'is_dla', 'is_dla_visible_arrival', 'is_dla_visible_departure',
                  'is_spf_visible', 'is_passengers_handling',

                  'availability',
                  'availability_bool',
                  ]

    def get_is_dla(self, obj):  # noqa
        if hasattr(obj, 'spf_version'):
            if obj.spf_version == 1:
                return obj.is_dla
            else:
                return obj.is_dla_v2
        return obj.is_dla_v2

    def get_is_dla_visible_arrival(self, obj):  # noqa
        if hasattr(obj, 'spf_version'):
            if obj.spf_version == 1:
                return obj.is_dla_visible_arrival
            else:
                return obj.is_dla_v2_visible_arrival
        return obj.is_dla_v2

    def get_is_dla_visible_departure(self, obj):  # noqa
        if hasattr(obj, 'spf_version'):
            if obj.spf_version == 1:
                return obj.is_dla_visible_departure
            else:
                return obj.is_dla_v2_visible_departure
        return obj.is_dla_v2

class HandlingServiceSimpleSerializer(serializers.ModelSerializer):
    """
    Second HandlingService serialized to display name only.
    """
    is_passengers_handling = serializers.SerializerMethodField()

    class Meta:
        model = HandlingService
        fields = ['id', 'name', 'codename', 'always_included',
                  'is_allowed_free_text', 'is_allowed_quantity_selection', 'is_passengers_handling', ]

    # TODO: Legacy https://aviationdatasolutions.slack.com/archives/C038P574EEN/p1678197540691449
    def get_is_passengers_handling(self, service):  # noqa
        return service.codename == 'passengers_handling'


class HandlingRequestServicesSerializer(serializers.ModelSerializer):
    service = HandlingServiceSimpleSerializer(many=False, read_only=True)
    booking_quantity_uom = UnitOfMeasurementSerializer(many=False, read_only=True)

    class Meta:
        model = HandlingRequestServices
        read_only_fields = (
            'id', 'movement', 'booking_confirmed', 'note',
            'booking_text', 'booking_quantity',
            'booking_quantity_uom',)
        fields = ['service', 'movement', 'booking_confirmed', 'note',
                  'booking_text', 'booking_quantity',
                  'booking_quantity_uom', ]


class HandlingRequestMovementDetailsSerializer(serializers.ModelSerializer):
    services = HandlingRequestServicesSerializer(many=True, read_only=True, source='hr_services')
    airport = AirportSerializer(many=False, read_only=True)

    class Meta:
        model = HandlingRequestMovement
        read_only_fields = ('id', 'direction', )
        fields = ['id', 'direction', 'date', 'date_local',
                  'airport', 'crew',
                  # Passengers
                  'is_passengers_onboard', 'is_passengers_tbc', 'passengers',
                  'passengers_tiny_repr', 'passengers_full_repr',

                  'comment', 'special_requests', 'ppr_number', 'services', ]


class HandlingRequestMovementSerializer(serializers.ModelSerializer):
    is_datetime_local = serializers.BooleanField(write_only=True, default=False)
    services = HandlingRequestServicesSerializer(
        many=True, read_only=True, source='hr_services')

    class Meta:
        model = HandlingRequestMovement
        read_only_fields = ('id', 'direction',)
        fields = ['id', 'direction', 'date',
                  'airport', 'crew', 'passengers', 'comment', 'special_requests', 'services', 'is_datetime_local',
                  'is_passengers_onboard', 'is_passengers_tbc', ]


class HandlingRequestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestType
        fields = ['id', 'name', ]


class FuelBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestFuelBooking
        fields = ['dla_contracted_fuel', 'fuel_release', ]


class HandlingRequestCrewMemberPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestCrewMemberPosition
        fields = ['id', 'name', ]


class HandlingRequestCrewSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    position = HandlingRequestCrewMemberPositionSerializer(read_only=True)

    class Meta:
        model = HandlingRequestCrew
        read_only_fields = ['id', 'person', 'position', 'is_primary_contact', ]
        fields = [
            # GET Fields
            'id', 'person', 'position', 'is_primary_contact', 'can_update_mission',
        ]


class HandlingRequestUpdatePrimaryContactSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    position = HandlingRequestCrewMemberPositionSerializer(read_only=True)

    person_id = RelatedFieldAlternative(required=True,
                                        write_only=True,
                                        source='person',
                                        queryset=Person.objects.all())
    position_id = RelatedFieldAlternative(required=True,
                                          write_only=True,
                                          source='position',
                                          queryset=HandlingRequestCrewMemberPosition.objects.all())

    class Meta:
        model = HandlingRequestCrew
        read_only_fields = ['id', 'person', 'position', 'is_primary_contact', ]
        fields = [
            # GET Fields
            'id', 'person', 'position', 'is_primary_contact', 'can_update_mission',
            # POST Fields
            'person_id', 'position_id',
        ]

    def create(self, validated_data, *args, **kwargs):
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        person = validated_data.get('person')

        organisation_people_qs = handling_request.customer_organisation.organisation_people.filter(person=person)
        if not organisation_people_qs.exists():
            raise serializers.ValidationError(
                detail={'person_id': ["Person does not belongs to S&F Request Organisation"]}, code='invalid_value')

        handling_request.mission_crew.filter(
            Q(person=person) | Q(is_primary_contact=True)
        ).delete()

        instance = HandlingRequestCrew(
            **validated_data,
            is_primary_contact=True,
            handling_request_id=handling_request_id)
        instance.save()

        return instance


class HandlingRequestSerializer(serializers.ModelSerializer):
    """
    Handling Request serializer perform creating request objects and all related things.
    """

    class RelatedFieldAlternative(serializers.PrimaryKeyRelatedField):

        def __init__(self, **kwargs):
            self.serializer = kwargs.pop('serializer', None)
            if self.serializer is not None and not issubclass(self.serializer, serializers.Serializer):
                raise TypeError('"serializer" is not a valid serializer class')

            super().__init__(**kwargs)

        def use_pk_only_optimization(self):
            return False if self.serializer else True

        def to_representation(self, instance):
            if self.serializer:
                return self.serializer(instance, context=self.context).data
            return super().to_representation(instance)

    arrival_movement = HandlingRequestMovementSerializer(many=False, write_only=True)
    departure_movement = HandlingRequestMovementSerializer(many=False, write_only=True)
    departure_movement_services = serializers.ListField(write_only=True, allow_empty=True, required=False)
    arrival_movement_services = serializers.ListField(write_only=True, allow_empty=True, required=False)
    movement = HandlingRequestMovementDetailsSerializer(many=True, read_only=True)
    ipa = serializers.SerializerMethodField(read_only=True)
    airport = HandlingLocationSerializer(many=False, read_only=True)
    airport_id = RelatedFieldAlternative(required=True, write_only=True, source='airport',
                                         queryset=Organisation.objects.handling_request_locations().all())
    handling_agent = HandlingAgentSerializer(many=False, read_only=True)
    fuel_booking_confirmed = serializers.SerializerMethodField()
    type = HandlingRequestTypeSerializer(many=False, read_only=True)
    type_id = RelatedFieldAlternative(required=True, write_only=True, source='type',
                                      queryset=HandlingRequestType.objects.all())
    feedback_submitted = serializers.SerializerMethodField()
    fuel_booking = FuelBookingSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()
    is_aog_available = serializers.SerializerMethodField()
    is_cancelable = serializers.SerializerMethodField()

    requesting_unit_id = RelatedFieldAlternative(required=False,
                                                 write_only=True,
                                                 queryset=Organisation.objects.aircraft_operator_military())
    primary_contact_id = RelatedFieldAlternative(required=False,
                                                 write_only=True,
                                                 queryset=Person.objects.all())
    request_reference = serializers.SerializerMethodField()
    crew = HandlingRequestCrewSerializer(many=True, read_only=True, source='mission_crew')
    created_by = PersonSerializer(many=False, read_only=True)
    conversation_id = serializers.SerializerMethodField()

    included_serializers = {
        'aircraft_type': AircraftTypeSerializer,
        'fuel_unit': UnitOfMeasurementSerializer,
    }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Represent ipa_name string in organisation format for future changes
        if data['ipa']:
            data['ipa'] = {
                'name': data['ipa'],
            }
        return data

    def get_status(self, obj):  # noqa
        return obj.get_full_status

    def get_is_editable(self, obj):  # noqa
        return getattr(obj, 'is_editable', None)

    def get_is_aog_available(self, obj):  # noqa
        return getattr(obj, 'is_aog_available', None)

    def get_is_cancelable(self, obj):  # noqa
        return getattr(obj, 'is_cancelable', None)

    def get_ipa(self, obj):  # noqa
        if hasattr(obj, 'fuel_booking'):
            ipa = getattr(obj.fuel_booking, 'ipa')
            return ipa.full_repr
        else:
            return None

    def get_fuel_booking_confirmed(self, obj):  # noqa
        return obj.is_fuel_booking_confirmed

    def get_feedback_submitted(self, obj):  # noqa
        return obj.feedback.exists()

    def get_request_reference(self, obj):  # noqa
        return obj.reference

    def get_conversation_id(self, obj):  # noqa
        conversation = obj.chat_conversations.first()
        return conversation.pk if conversation else None

    class JSONAPIMeta:
        included_resources = ['aircraft_type', 'fuel_unit']

    class Meta:
        model = HandlingRequest
        read_only_fields = ['id', 'fuel_booking_confirmed', 'request_reference',
                            'decline_reason',
                            'ipa', 'parking_apron', 'parking_stand', 'handling_agent',
                            'feedback_submitted', 'fuel_booking', 'is_editable', 'is_standalone', 'is_aog_available',
                            'created_by', 'is_pdf_available', ]

        fields = ['id', 'callsign', 'tail_number', 'mission_number', 'apacs_number', 'type', 'type_id',
                  'decline_reason',
                  'cancelled', 'parking_apron', 'parking_stand', 'handling_agent', 'status',
                  'airport', 'notify_dao', 'feedback_submitted', 'aircraft_type',
                  'is_standalone', 'is_editable', 'is_cancelable', 'is_aog_available',
                  'crew', 'created_by', 'is_pdf_available', 'conversation_id',

                  # Staff endpoint related fields
                  'requesting_unit_id', 'primary_contact_id', 'request_reference',
                  # Fuel
                  'fuel_required', 'fuel_quantity', 'fuel_unit',
                  'fuel_captains_request', 'fuel_booking_confirmed',
                  'fuel_booking', 'ipa', 'fuel_prist_required',
                  # Movements
                  'movement', 'arrival_movement', 'departure_movement',
                  'departure_movement_services', 'arrival_movement_services', 'airport_id']

    def validate(self, data):
        # Validate if user have organization
        request_user = getattr(self.context['request'], 'user')
        request_person = getattr(request_user, 'person')

        if not request_user.is_staff:
            if not request_user.person.organisations.exists():
                raise serializers.ValidationError(
                    detail='Submitting user have no organisation to submit S&F Request.', code='invalid_value')

        # Skip validation on partial update
        if self.partial:
            return data

        # Validate for duplicate
        arrival_movement_fields = data.get('arrival_movement')
        departure_movement_fields = data.get('departure_movement')
        arrival_is_datetime_local = arrival_movement_fields.get('is_datetime_local')
        departure_is_datetime_local = departure_movement_fields.get('is_datetime_local')

        instance_airport = self.instance.airport if self.instance else None
        airport = data.get('airport', None) or instance_airport

        instance_tail_number_id = self.instance.tail_number.pk if self.instance and self.instance.tail_number else None
        tail_number_id = data.get('tail_number_id') or instance_tail_number_id

        requesting_unit = data.pop('requesting_unit_id', None)
        primary_contact = data.pop('primary_contact_id', None)

        if not self.instance:
            if request_user.is_staff:
                if not requesting_unit:
                    raise serializers.ValidationError(
                        detail='requesting_unit_id required', code='invalid_value')

                if not primary_contact:
                    raise serializers.ValidationError(
                        detail='primary_contact_id should be submitted',
                        code='invalid_value')

                if not requesting_unit.organisation_people.filter(person=primary_contact).exists():
                    raise serializers.ValidationError(
                        detail='Selected person does not belongs to given organisation',
                        code='invalid_value')

                data['requesting_unit'] = requesting_unit
                data['primary_contact'] = primary_contact
            else:
                # Fallback set of primary contact for Flight Crew users
                if not request_user.is_dod_planners_perms and not primary_contact:
                    primary_contact = request_person

                # Raise error if primary_contact_id not submitted
                if not primary_contact:
                    raise serializers.ValidationError(
                        detail='primary_contact_id should be submitted',
                        code='invalid_value')

                data['requesting_unit'] = primary_contact.main_organisation
                data['primary_contact'] = primary_contact

        if arrival_is_datetime_local:
            arrival_date = get_utc_from_airport_local_time(local_datetime=arrival_movement_fields.get('date'),
                                                           organisation=airport)
        else:
            arrival_date = arrival_movement_fields.get('date')

        if departure_is_datetime_local:
            departure_date = get_utc_from_airport_local_time(local_datetime=departure_movement_fields.get('date'),
                                                             organisation=airport)
        else:
            departure_date = departure_movement_fields.get('date')

        if self.instance:
            requesting_unit = self.instance.customer_organisation
        else:
            requesting_unit = data['requesting_unit']

        duplicate_found = validate_handling_request_for_duplicate_v2(
            organisation_id=requesting_unit.pk,
            callsign=data.get('callsign'),
            arrival_date=arrival_date,
            departure_date=departure_date,
            tail_number_id=tail_number_id,
            airport_id=data.get('airport').pk,
            mission_number=data.get('mission_number'),
            exclude_id=self.instance.pk if self.instance else None,
        )

        if duplicate_found:
            raise serializers.ValidationError(
                detail='A servicing & fueling request already exists with these details.', code='invalid_value')

        if arrival_date < timezone.now():
            raise serializers.ValidationError(detail="Arrival date can't be in the past", code='invalid_value')

        return data

    def update(self, instance, validated_data):
        request_person = self.context['request'].user.person
        ignored_fields = ['notify_dao', 'primary_contact_id', ]
        old_instance_diff = generate_diff_dict(handling_request=instance)
        instance.updated_by = request_person
        instance.supress_amendment = True

        if not self.partial:
            for ignored_field in ignored_fields:
                validated_data.pop(ignored_field, None)

            arrival_movement_fields = validated_data.pop('arrival_movement')
            departure_movement_fields = validated_data.pop('departure_movement')
            arrival_is_datetime_local = arrival_movement_fields.pop('is_datetime_local')
            departure_is_datetime_local = departure_movement_fields.pop('is_datetime_local')

            if 'departure_movement_services' in validated_data:
                departure_movement_services_fields = validated_data.pop('departure_movement_services')
            else:
                departure_movement_services_fields = []

            if 'arrival_movement_services' in validated_data:
                arrival_movement_services_fields = validated_data.pop('arrival_movement_services')
            else:
                arrival_movement_services_fields = []

            # Arrival movement amendment
            arrival_movement = instance.movement.filter(direction_id='ARRIVAL').first()
            arrival_movement.request.supress_amendment = True  # Prevent duplicate notifications
            arrival_movement.updated_by = request_person
            for field, value in arrival_movement_fields.items():
                new_value = value
                old_value = getattr(arrival_movement, field)
                if field == 'date':
                    if arrival_is_datetime_local:
                        new_value = get_utc_from_airport_local_time(new_value, instance.airport)
                setattr(arrival_movement, field, new_value)

            arrival_movement.save()
            if arrival_movement.is_amended:
                instance.is_movement_amended = True

            if arrival_movement_services_fields:
                handling_reqeust_create_service_booking(
                    services=arrival_movement_services_fields,
                    movement=arrival_movement,
                    handling_request=instance,
                    amend=True,
                    person=request_person)

            # Departure movement amendment
            departure_movement = instance.departure_movement
            departure_movement.request.supress_amendment = True  # Prevent duplicate notifications
            departure_movement.updated_by = request_person
            for field, value in departure_movement_fields.items():
                new_value = value
                old_value = getattr(departure_movement, field)
                if field == 'date':
                    if departure_is_datetime_local:
                        new_value = get_utc_from_airport_local_time(new_value, instance.airport)
                setattr(departure_movement, field, new_value)

            departure_movement.save()
            if departure_movement.is_amended:
                instance.is_movement_amended = True

            if departure_movement_services_fields:
                handling_reqeust_create_service_booking(
                    services=departure_movement_services_fields,
                    movement=departure_movement,
                    handling_request=instance,
                    amend=True,
                    person=request_person)

        if self.partial and 'cancelled' in validated_data:
            handling_request_cancel_actions(
                handling_request=instance,
                author=getattr(self.context['request'].user, 'person', None),
            )

        delattr(instance, 'supress_amendment')
        instance.old_instance_diff = old_instance_diff
        instance = super().update(instance, validated_data)

        instance.activity_log.create(
            author=request_person,
            record_slug='sfr_amended',
            details='Servicing & Fueling Request has been amended',
        )

        # Fetch instance with updated status from database
        instance = HandlingRequest.objects.with_status().filter(pk=instance.pk).first()

        return instance

    def create(self, validated_data):
        arrival_movement_fields = validated_data.pop('arrival_movement')
        departure_movement_fields = validated_data.pop('departure_movement')
        arrival_is_datetime_local = arrival_movement_fields.pop('is_datetime_local')
        departure_is_datetime_local = departure_movement_fields.pop('is_datetime_local')

        request_user = getattr(self.context['request'], 'user')
        author_person = getattr(request_user, 'person')

        requesting_unit = validated_data.pop('requesting_unit', None)
        primary_contact = validated_data.pop('primary_contact', None)

        if 'departure_movement_services' in validated_data:
            departure_movement_services_fields = validated_data.pop('departure_movement_services')
        else:
            departure_movement_services_fields = None

        if 'arrival_movement_services' in validated_data:
            arrival_movement_services_fields = validated_data.pop('arrival_movement_services')
        else:
            arrival_movement_services_fields = None

        app_version = get_mobile_app_version(self.context['request'])

        # Save objects
        instance = HandlingRequest(
            **validated_data,
            created_by=author_person,
            customer_organisation=requesting_unit)
        instance.is_standalone = True
        instance.skip_signal = True
        instance.meta_creation_source = 'Mobile App'
        instance.save()
        delattr(instance, 'skip_signal')

        arrival_movement = HandlingRequestMovement(request=instance, direction_id='ARRIVAL',
                                                   **arrival_movement_fields)
        arrival_movement.is_datetime_local = arrival_is_datetime_local
        if app_version <= '1.1.18':
            if arrival_movement.passengers and arrival_movement.passengers > 0:
                arrival_movement.is_passengers_onboard = True
        arrival_movement.save()

        departure_movement = HandlingRequestMovement(request=instance, direction_id='DEPARTURE',
                                                     **departure_movement_fields)
        departure_movement.is_datetime_local = departure_is_datetime_local
        if app_version <= '1.1.18':
            if departure_movement.passengers and departure_movement.passengers > 0:
                departure_movement.is_passengers_onboard = True
        departure_movement.save()

        if departure_movement_services_fields:
            handling_reqeust_create_service_booking(
                services=departure_movement_services_fields,
                movement=departure_movement,
                handling_request=instance,
                person=author_person)

        if arrival_movement_services_fields:
            handling_reqeust_create_service_booking(
                services=arrival_movement_services_fields,
                movement=arrival_movement,
                handling_request=instance,
                person=author_person)

        # Assign submitting user to the crew
        handling_request_crew = HandlingRequestCrew(
            handling_request=instance,
            person=primary_contact,
            is_primary_contact=True
        )
        handling_request_crew.skip_signal = True
        handling_request_crew.save()

        # Send Handling Request receive confirmation push
        handling_request_received_push_notification.apply_async(args=(instance.id,), countdown=2)

        # Trigger post_save signal to create/update fuel order
        post_save.send(HandlingRequest, instance=instance, created=True)

        return instance


class HandlingRequestCheckForDuplicateSerializer(serializers.Serializer):
    callsign = serializers.CharField(required=False)
    airport_id = serializers.IntegerField()
    tail_number_id = serializers.IntegerField(required=False)
    arrival_date = serializers.DateTimeField()
    departure_date = serializers.DateTimeField(required=False)
    organisation_id = serializers.IntegerField()
    mission_number = serializers.CharField(required=False)

    arrival_is_datetime_local = serializers.BooleanField(write_only=True, default=False)
    departure_is_datetime_local = serializers.BooleanField(write_only=True, default=False)

    def check_for_duplicate(self):
        self.is_valid()
        fields = self._validated_data
        organisation_id = fields['organisation_id']
        callsign = fields.get('callsign', None)
        airport_id = fields['airport_id']
        tail_number_id = fields.get('tail_number_id')
        mission_number = fields.get('mission_number')

        arrival_date = fields['arrival_date']
        departure_date = fields.get('departure_date')
        arrival_is_datetime_local = fields.get('arrival_is_datetime_local')
        departure_is_datetime_local = fields.get('departure_is_datetime_local')

        # Convert local time to UTC
        if arrival_is_datetime_local:
            arrival_date = get_utc_from_airport_local_time(local_datetime=arrival_date,
                                                           organisation=Organisation.objects.get(pk=airport_id))

        if departure_is_datetime_local:
            departure_date = get_utc_from_airport_local_time(local_datetime=departure_date,
                                                             organisation=Organisation.objects.get(pk=airport_id))

        app_version = get_mobile_app_version(self.context['request'])
        # Check if user have access to the given organisation
        request_user = self.context['request'].user
        request_person = request_user.person

        if not request_user.is_staff:
            position = request_person.primary_dod_position
            organisation = position.organisation
            if not position:
                raise serializers.ValidationError(
                    detail={'organisation_id': ["Invalid organisation ID"]})
        else:
            organisation = Organisation.objects.get(pk=organisation_id)

        # TODO: Temporary workaround
        if not callsign:
            import sentry_sdk
            sentry_sdk.capture_message("Legacy Request Usage (Duplicate checking with no callsign supplied)", "error")
            return False, None

        if app_version <= '1.1.29':
            duplicate_found = validate_handling_request_for_duplicate(
                organisation_id=organisation.pk,
                callsign=callsign,
                arrival_date=arrival_date,
                airport_id=airport_id,
                mission_number=mission_number,
            )
        else:
            duplicate_found = validate_handling_request_for_duplicate_v2(
                organisation_id=organisation.pk,
                callsign=callsign,
                arrival_date=arrival_date,
                departure_date=departure_date,
                tail_number_id=tail_number_id,
                airport_id=airport_id,
                mission_number=mission_number,
            )

        if duplicate_found:
            exists = True
            callsign = callsign
        else:
            exists = False
            callsign = callsign

        return exists, callsign


class SetAirCardSerializer(serializers.Serializer):
    callsign = serializers.CharField(max_length=50)
    air_card_prefix_id = serializers.IntegerField()
    air_card_number = serializers.IntegerField()
    air_card_expiration = serializers.CharField(max_length=5)
    air_card_photo = serializers.FileField(write_only=True, required=False)

    def validate_air_card_number(self, value):  # noqa
        return aircard_number_validation_simple(value)

    def validate_air_card_expiration(self, value):  # noqa
        validation_result = aircard_expiration_validation(value)
        if validation_result is False:
            raise serializers.ValidationError(
                detail='AIR Card expired', code='invalid_value')
        return value

    def create(self, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        person_position = request_person.primary_dod_position
        air_card_photo = self.context['request'].FILES.get('air_card_photo')

        # Build QuerySet
        handling_requests_by_callsign_qs = person_position.get_sfr_list(managed=True).filter(
            callsign=validated_data.get('callsign'))

        # Update affected Handling Request
        if handling_requests_by_callsign_qs.exists():
            if air_card_photo:
                from django.core.files.base import ContentFile
                air_card_photo_file = ContentFile(air_card_photo.read(), 'air_card_photo.png')

            for handling_request in handling_requests_by_callsign_qs:
                if air_card_photo:
                    air_card_photo_file.name = f'aircard_photo_{handling_request}_{handling_request.callsign}.png'
                    handling_request.air_card_photo = air_card_photo_file

                air_card_prefix_id = validated_data.get('air_card_prefix_id')
                air_card_prefix = AirCardPrefix.objects.filter(
                    pk=air_card_prefix_id).first()

                handling_request.air_card_prefix = air_card_prefix
                handling_request.air_card_number = validated_data.get('air_card_number')
                handling_request.air_card_expiration = validated_data.get('air_card_expiration')
                handling_request.save()

        else:
            raise exceptions.NotFound(
                detail='No Handling Request with provided callsign', code='not_found')
        return handling_requests_by_callsign_qs.first()


class DLAHandlingServiceSerializer(serializers.ModelSerializer):
    """DLA HandlingService serializer to display name and DLA options."""
    class Meta:
        model = HandlingService
        fields = ['id', 'name', 'is_spf_visible', ]


class ServiceProvisionFormToCompleteSerializer(serializers.ModelSerializer):
    spf_complete = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    air_card_submitted = serializers.SerializerMethodField()
    airport = AirportSerializer()
    comment = serializers.SerializerMethodField()
    trip_start = serializers.SerializerMethodField()
    trip_end = serializers.SerializerMethodField()

    def get_trip_start(self, obj):  # noqa
        if hasattr(obj, 'trip_start'):
            return obj.trip_start

    def get_trip_end(self, obj):  # noqa
        if hasattr(obj, 'trip_end'):
            return obj.trip_end

    def get_spf_complete(self, obj):  # noqa
        if hasattr(obj, 'spf_complete'):
            return obj.spf_complete

    def get_services(self, obj):  # noqa
        items = HandlingService.objects.filter(
            Q(is_active=True, is_dla=True, is_spf_visible=True, custom_service_for_request__isnull=True) |
            Q(is_dla=True, is_spf_visible=True, custom_service_for_request=obj)
        ).only('id', 'name', 'is_spf_visible').order_by('name').all()

        serializer = DLAHandlingServiceSerializer(instance=items, many=True)
        return serializer.data

    # noinspection PyMethodMayBeStatic
    def get_air_card_submitted(self, obj):
        return all([bool(obj.air_card_number), bool(obj.air_card_expiration)])

    def get_comment(self, obj):  # noqa
        if hasattr(obj, 'spf'):
            return obj.spf.customer_comment

    class Meta:
        model = HandlingRequest
        read_only_fields = ('id',)
        fields = ['id', 'trip_start', 'trip_end', 'spf_complete',
                  'air_card_submitted', 'callsign', 'airport', 'comment', 'services', ]


class HandlingRequestUpdateApacsNumberSerializer(serializers.ModelSerializer):
    # TODO: Deprecated 2022-08-12
    class Meta:
        model = HandlingRequest
        read_only_fields = ['id', ]
        fields = ['id', 'apacs_number', ]


class HandlingRequestUpdateApacsNumberSerializerNew(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequest
        read_only_fields = ['id', ]
        fields = ['id', 'apacs_number', ]

    def to_representation(self, instance):
        return HandlingRequestSerializer(instance, context=self.context).data


class HandlingRequestAircraftOnGroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequest
        read_only_fields = ['id', ]
        fields = ['id', ]

    def to_representation(self, handling_request):
        from api.serializers.handling_admin import HandlingRequestSerializer as StaffHandlingRequestSerializer
        handling_request = HandlingRequest.objects.with_eta_etd_and_status_index().get(pk=handling_request.pk)
        if self.context['request'].user.is_staff:
            return StaffHandlingRequestSerializer(handling_request, context=self.context).data
        else:
            return HandlingRequestSerializer(handling_request, context=self.context).data

    def update(self, handling_request, validated_data):
        request_person = self.context['request'].user.person
        handling_request.updated_by = request_person
        handling_request.is_aog = True
        handling_request = super().update(handling_request, validated_data)
        return handling_request


class HandlingRequestAircraftServiceableSerializer(serializers.ModelSerializer):
    is_datetime_local = serializers.BooleanField(write_only=True, default=False)

    class Meta:
        model = HandlingRequestMovement
        read_only_fields = ['id', 'direction', ]
        fields = ['id',
                  'date', 'is_datetime_local',
                  'airport', 'crew',
                  'is_passengers_onboard', 'is_passengers_tbc', 'passengers',
                  ]

    def to_representation(self, movement):
        handling_request = HandlingRequest.objects.with_eta_etd_and_status_index().get(pk=movement.request.pk)
        from api.serializers.handling_admin import HandlingRequestSerializer as StaffHandlingRequestSerializer
        if self.context['request'].user.is_staff:
            return StaffHandlingRequestSerializer(handling_request, context=self.context).data
        else:
            return HandlingRequestSerializer(handling_request, context=self.context).data

    def update(self, movement, validated_data):
        request_person = self.context['request'].user.person
        movement.updated_by = request_person
        movement.request.updated_by = request_person
        movement.request.is_aog = False
        movement.request.save()
        movement = super().update(movement, validated_data)
        return movement


class ServiceProvisionFormSerializer(serializers.ModelSerializer):
    taken_services = serializers.ListField(write_only=True, required=False)
    untaken_services = serializers.ListField(write_only=True, required=False)

    class Meta:
        model = ServiceProvisionForm
        read_only_fields = ['handling_request', ]
        fields = ['handling_request', 'customer_comment',
                  'customer_signature', 'taken_services', 'untaken_services', ]

    def create(self, validated_data):
        handling_request_id = self.context.get('view').kwargs.get('handling_request')
        request_person = getattr(self.context['request'].user, 'person')
        person_position = request_person.primary_dod_position
        taken_services = None
        untaken_services = None

        if 'taken_services' in validated_data:
            taken_services = validated_data.pop('taken_services')
        if 'untaken_services' in validated_data:
            untaken_services = validated_data.pop('untaken_services')

        # Check is HandlingRequest PK supplied
        if not handling_request_id:
            raise serializers.ValidationError(
                code='required',
                detail={'handling_request': ["Please specify Handling Request"]})

        # Get corresponding S&F Request if user has access otherwise throw 404
        try:
            handling_request = person_position.get_sfr_list(managed=True).get(pk=handling_request_id)
        except HandlingRequest.DoesNotExist:
            raise NotFound(detail="No such S&F Request", code=404)

        # Check is SPF not yet exists for corresponding S&F Request
        if ServiceProvisionForm.objects.filter(handling_request_id=handling_request_id).exists():
            raise serializers.ValidationError(
                code='duplicate',
                detail={'handling_request': ["There is already SPF for this Handling Request"]})

        # Create SPF
        instance = ServiceProvisionForm.objects.create(handling_request=handling_request, **validated_data)

        # Add services list to SPF
        if taken_services:
            ServiceProvisionFormServiceTaken.objects.bulk_create(
                [ServiceProvisionFormServiceTaken(spf=instance, taken=True, service_id=service_id) for service_id in
                 taken_services])

        if untaken_services:
            ServiceProvisionFormServiceTaken.objects.bulk_create(
                [ServiceProvisionFormServiceTaken(spf=instance, taken=False, service_id=service_id) for service_id in
                 untaken_services])

        # Generate SPF PDF, send push, emails and staff notifications
        from handling.tasks import spf_submission_post_processing
        spf_submission_post_processing.delay(instance.id)

        return instance

    def update(self, instance, validated_data):
        taken_services = None
        untaken_services = None

        services_data = ServiceProvisionFormSerializer(
            data=self.context['request'].data,
            context=self.context['request']
        )
        services_data.is_valid()
        request_data = services_data.validated_data

        if 'taken_services' in request_data:
            taken_services = request_data.pop('taken_services')
            ServiceProvisionFormServiceTaken.objects.filter(spf=instance).delete()
        if 'untaken_services' in request_data:
            untaken_services = request_data.pop('untaken_services')
            ServiceProvisionFormServiceTaken.objects.filter(spf=instance).delete()

        if taken_services:
            ServiceProvisionFormServiceTaken.objects.bulk_create(
                [ServiceProvisionFormServiceTaken(spf=instance, taken=True, service_id=service_id) for service_id in
                 taken_services])

        if untaken_services:
            ServiceProvisionFormServiceTaken.objects.bulk_create(
                [ServiceProvisionFormServiceTaken(spf=instance, taken=False, service_id=service_id) for service_id in
                 untaken_services])

        # Save the instance using new data
        instance = super().update(instance, validated_data)

        # Generate SPF PDF, send push, emails and staff notifications
        from handling.tasks import spf_submission_post_processing
        spf_submission_post_processing.delay(instance.id)

        return instance


class HandlingRequestFeedbackSerializer(serializers.ModelSerializer):
    callsign = serializers.CharField(read_only=True, source='handling_request.callsign')

    class Meta:
        model = HandlingRequestFeedback
        read_only_fields = ['created_at', ]
        fields = ['fuelling_feedback', 'servicing_feedback', 'created_at', 'callsign', ]

    # TODO: Deprecated 2022-08-12
    def create(self, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        person_position = request_person.primary_dod_position
        handling_request_id = self.context.get('view').kwargs.get('pk')

        # Check if user have access to the given organisation
        request_exists = person_position.get_sfr_list().filter(pk=handling_request_id).exists()

        if not request_exists:
            raise serializers.ValidationError(
                detail={'handling_request_id': ["Invalid Handling Request ID"]})

        instance = HandlingRequestFeedback.objects.create(
            **validated_data,
            handling_request_id=handling_request_id)

        return instance


class HandlingRequestDetailedFeedbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = HandlingRequestFeedback
        fields = ['fuelling_feedback', 'servicing_feedback', ]

    def to_representation(self, instance):
        handling_request = getattr(instance, 'handling_request', None)
        if handling_request:
            handling_request_qs = HandlingRequest.objects.with_status().filter(pk=handling_request.pk)
            handling_request_qs = handling_request_qs.annotate(is_editable=Value(True))
            handling_request_with_extra = handling_request_qs.first()
            return HandlingRequestSerializer(handling_request_with_extra, context=self.context).data

    def create(self, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        person_position = request_person.primary_dod_position
        handling_request_id = self.context.get('view').kwargs.get('pk')

        # Check if user have access to the given organisation
        request_exists = person_position.get_sfr_list().filter(pk=handling_request_id).exists()

        if not request_exists:
            raise serializers.ValidationError(
                detail={'handling_request_id': ["Invalid Handling Request ID"]})

        instance = HandlingRequestFeedback.objects.create(
            **validated_data,
            handling_request_id=handling_request_id)

        return instance
