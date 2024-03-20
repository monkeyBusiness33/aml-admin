from django.db import transaction
from rest_framework import serializers
from api.serializers.core import AirCardPrefixSimpleSerializer
from api.serializers.handling_base import HandlingLocationSerializer
from api.serializers.handling_request_crew import HandlingRequestCrewSerializer
from api.utils.helpers import get_mobile_app_version
from core.models import AirCardPrefix, UnitOfMeasurement
from core.utils.validators import aircard_expiration_validation
from handling.models import HandlingRequest, HandlingRequestMovement, HandlingRequestServices, HandlingService, \
    ServiceProvisionForm, ServiceProvisionFormServiceTaken, \
    HandlingRequestType, HandlingRequestFuelBooking, MovementDirection, AutoServiceProvisionForm
from api.serializers.aircraft import AircraftTypeSerializer, TailNumberSerializer
from api.serializers.airport import AirportSerializer
from handling.serializers import HandlingServiceSimpleSerializer
from api.serializers.organisation import OrganisationSerializer, OrganisationDetailsSerializer, \
    HandlerOrganisationSerializer
from api.serializers.user import PersonSerializer
from handling.utils.handling_request_func import unable_to_support_actions
from handling.utils.spf_auto import generate_auto_spf_email
from organisation.models import Organisation, OrganisationDetails, IpaDetails, OrganisationRestricted, HandlerDetails, \
    DLAContractLocation
from api.utils.related_field import RelatedFieldAlternative
from aircraft.models import AircraftHistory


class HandlingRequestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestType
        fields = ['id', 'name', ]


class HandlingRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer with the limited fields set to return minimum required data
    to build list of the requests.
    """
    aircraft_type = AircraftTypeSerializer()
    # TODO: 'customer_person' S&F Request filed deprecated
    customer_person = PersonSerializer(source='primary_contact')
    crew = HandlingRequestCrewSerializer(many=True, source='mission_crew')
    customer_organisation = OrganisationSerializer(read_only=True)
    created_by = PersonSerializer()
    airport = HandlingLocationSerializer()
    status = serializers.SerializerMethodField()
    eta_date = serializers.DateTimeField()

    class Meta:
        model = HandlingRequest
        fields = ['id', 'callsign', 'eta_date', 'created_at', 'created_by', 'customer_person', 'crew',
                  'customer_organisation', 'airport', 'aircraft_type', 'status', ]

    def get_status(self, obj):
        return obj.get_full_status

    def get_eta_date(self, obj):
        return obj.eta_date


class HandlingRequestCalendarSerializer(serializers.ModelSerializer):
    """
    Serializer with the limited fields set to return minimum required data
    to build calendar of the S&F Requests.
    """
    aircraft_type = AircraftTypeSerializer()
    tail_number = TailNumberSerializer(many=False)
    airport = HandlingLocationSerializer()
    status = serializers.SerializerMethodField()
    fuel_status = serializers.SerializerMethodField()
    ground_handling_status = serializers.SerializerMethodField()
    eta_date = serializers.DateTimeField()
    etd_date = serializers.DateTimeField()
    assigned_person_initials = serializers.SerializerMethodField()

    class Meta:
        model = HandlingRequest
        fields = ['id', 'callsign', 'eta_date', 'etd_date',
                  'airport', 'aircraft_type', 'tail_number', 'assigned_person_initials',
                  'status', 'fuel_status', 'ground_handling_status', ]

    def get_status(self, obj): # noqa
        return obj.get_full_status

    def get_fuel_status(self, obj): # noqa
        return obj.fuel_status

    def get_ground_handling_status(self, obj): # noqa
        return obj.ground_handling_status

    def get_eta_date(self, obj): # noqa
        return obj.eta_date

    def get_etd_date(self, obj): # noqa
        return obj.etd_date

    def get_assigned_person_initials(self, obj): # noqa
        if not obj.assigned_mil_team_member:
            return '--'
        else:
            return obj.assigned_mil_team_member.initials


class HandlingRequestCustomServiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer to create "Custom Service" for the S&F Request
    """
    handling_request_id = serializers.IntegerField(required=True, write_only=True)

    class Meta:
        model = HandlingService
        read_only_fields = ['id', ]
        fields = ['id', 'name', 'handling_request_id', ]

    def create(self, validated_data, *args, **kwargs):
        handling_request_id = validated_data.pop('handling_request_id')
        handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()

        if not handling_request:
            raise serializers.ValidationError("Wrong S&F identifier")

        instance = HandlingService.objects.create(
            **validated_data,
            is_active=False,
            custom_service_for_request=handling_request,
        )

        return instance


class HandlingRequestServicesSerializer(serializers.ModelSerializer):
    updated_by = PersonSerializer(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        service_serializer = HandlingServiceSimpleSerializer(instance=instance.service, many=False)
        data['service'] = service_serializer.data

        return data

    def validate(self, data):
        booking_quantity = data.get('booking_quantity', None)
        booking_text = data.get('booking_text', None)
        if all([booking_quantity, booking_text]):
            raise serializers.ValidationError(
                "Both 'Text Requirements' and 'Service Quantity' are submitted, should be one of them")
        return data

    def create(self, handling_request_service, *args, **kwargs):
        handling_request_service.updated_by = getattr(self.context['request'].user, 'person')
        handling_request_service = super().create(handling_request_service)
        return handling_request_service

    class Meta:
        model = HandlingRequestServices
        read_only_fields = ('id', 'booking_confirmed', 'updated_at', 'updated_by',)
        fields = ['id', 'service', 'movement', 'booking_confirmed',
                  'booking_text', 'booking_quantity',
                  'note', 'updated_at', 'updated_by',
                  'note_internal', 'is_service_deletable', ]


class HandlingRequestMovementSerializer(serializers.ModelSerializer):
    services = HandlingRequestServicesSerializer(many=True, read_only=True, source='hr_services')
    booking_completed = serializers.SerializerMethodField()
    airport = AirportSerializer()
    airport_id = RelatedFieldAlternative(required=False, write_only=True, source='airport',
                                         allow_null=True,
                                         queryset=Organisation.objects.airport())
    is_datetime_local = serializers.BooleanField(write_only=True, default=False)

    def get_booking_completed(self, obj):
        return obj.booking_completed

    def update(self, instance, validated_data):
        request_user = getattr(self.context['request'], 'user')
        author_person = getattr(request_user, 'person')
        app_version = get_mobile_app_version(self.context['request'])
        instance.updated_by = author_person

        if app_version <= '1.1.18':
            passengers = validated_data.pop('passengers', None)
            if passengers and passengers > 0:
                instance.is_passengers_onboard = True

        if app_version >= '1.1.19':
            is_passengers_onboard = validated_data.pop('is_passengers_onboard', None)
            is_passengers_tbc = validated_data.pop('is_passengers_tbc', None)
            passengers = validated_data.pop('passengers', None)

            if is_passengers_onboard:
                instance.is_passengers_onboard = True

                if is_passengers_tbc:
                    instance.is_passengers_tbc = True
                    instance.passengers = None

                if not is_passengers_tbc:
                    if not passengers or passengers == 0:
                        raise serializers.ValidationError("Passengers count should be submitted")
                    instance.is_passengers_tbc = False
                    instance.passengers = passengers

            if is_passengers_onboard is False:
                instance.is_passengers_onboard = False
                instance.is_passengers_tbc = False
                instance.passengers = None

        return super().update(instance, validated_data)

    class Meta:
        model = HandlingRequestMovement
        read_only_fields = ('id', 'direction', )
        fields = ['id', 'booking_completed', 'ppr_number',
                  'direction', 'date', 'is_datetime_local',
                  'airport_id', 'airport',
                  'crew',

                  # Passengers
                  'is_passengers_onboard', 'is_passengers_tbc', 'passengers',
                  'passengers_tiny_repr', 'passengers_full_repr',

                  'comment', 'special_requests', 'services', ]


class HandlingServiceSerializer(serializers.ModelSerializer):
    '''
    HandlingService serialized to display name and status.
    '''

    class Meta:
        model = HandlingService
        fields = ['id', 'name', ]


class ServiceProvisionFormServiceTakenSerializer(serializers.ModelSerializer):
    '''
    Serialize SPF DLA service taken state
    '''
    service = HandlingServiceSerializer()

    class Meta:
        model = ServiceProvisionFormServiceTaken
        fields = ['id', 'taken', 'service', ]


class ServiceProvisionFormSerializer(serializers.ModelSerializer):
    '''
    Admin SPF serializer
    '''
    dla_services = serializers.SerializerMethodField()
    custom_services = serializers.SerializerMethodField()

    def get_dla_services(self, obj):
        '''
        Get DLA Services for the SPF
        '''
        items = obj.dla_services_list
        serializer = ServiceProvisionFormServiceTakenSerializer(
            instance=items, many=True)
        return serializer.data

    def get_custom_services(self, obj):
        '''
        Get Custom Services for the SPF
        '''
        items = obj.custom_services_list_api
        serializer = ServiceProvisionFormServiceTakenSerializer(
            instance=items, many=True)
        return serializer.data

    class Meta:
        model = ServiceProvisionForm
        fields = ['id', 'customer_comment', 'spf_document', 'created_at',
                  'dla_services', 'custom_services', ]


class FuelDlaContractSerializer(serializers.ModelSerializer):
    supplier = OrganisationSerializer(many=False)

    class Meta:
        model = DLAContractLocation
        fields = ['supplier', ]


class FuelBookingSerializer(serializers.ModelSerializer):
    ipa = OrganisationSerializer(read_only=True)
    ipa_id = RelatedFieldAlternative(required=True, write_only=True, source='ipa',
                                     queryset=Organisation.objects.ipa())

    fuel_required_on = serializers.ChoiceField(required=False, write_only=True,
                                               choices=HandlingRequest.FUEL_REQUIRED_CHOICES)

    fuel_quantity = serializers.IntegerField(required=False, write_only=True)
    fuel_unit_id = RelatedFieldAlternative(required=False, write_only=True, queryset=UnitOfMeasurement.objects.all())
    fuel_prist_required = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = HandlingRequestFuelBooking
        fields = [
            'dla_contracted_fuel',
            'fuel_order_number',
            'fuel_release',
            'ipa',
            'ipa_id',
            'fuel_required_on',
            'fuel_quantity',
            'fuel_unit_id',
            'fuel_prist_required',
        ]

    def validate(self, data):
        dla_contracted_fuel = data.get('dla_contracted_fuel', None)
        fuel_order_number = data.get('fuel_order_number', None)
        fuel_release = data.get('fuel_release', None)
        if not dla_contracted_fuel:
            if not any([fuel_order_number, fuel_release]):
                raise serializers.ValidationError(
                    "Fuel Order Number and Fuel Release File Required")

        # Validate IPA
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        ipa = data.get('ipa')
        if not ipa.ipa_locations.filter(pk=handling_request.airport.pk).exists():
            raise serializers.ValidationError(
                detail={'ipa_id': ["Selected IPA does not servicing in S&F Request's airport"]}, code='invalid_value')

        # Validate Fuel details if it submitted
        fuel_required_on = data.get('fuel_required_on', None)
        fuel_quantity = data.get('fuel_quantity', None)
        fuel_unit = data.get('fuel_unit_id', None)
        fuel_prist_required = data.get('fuel_prist_required', None)

        if fuel_required_on and fuel_required_on != 'NO_FUEL':
            if not fuel_quantity:
                raise serializers.ValidationError(
                    detail={'fuel_quantity': ["Fuel quantity should be submitted"]}, code='invalid_value')

            if not fuel_unit:
                raise serializers.ValidationError(
                    detail={'fuel_unit': ["Fuel unit should be submitted"]}, code='invalid_value')

            if fuel_prist_required is None:
                raise serializers.ValidationError(
                    detail={'fuel_prist_required': ['"Fuel Prist Required" should be submitted']}, code='invalid_value')

        return data

    def create(self, validated_data, *args, **kwargs):
        request_person = getattr(self.context['request'].user, 'person')
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)

        if HandlingRequestFuelBooking.objects.filter(handling_request=handling_request).exists():
            raise serializers.ValidationError('Fuel Booking for this S&F Request already processed')

        fuel_required_on = validated_data.pop('fuel_required_on', None)
        fuel_quantity = validated_data.pop('fuel_quantity', None)
        fuel_unit = validated_data.pop('fuel_unit_id', None)
        fuel_prist_required = validated_data.pop('fuel_prist_required', None)

        fuel_booking = HandlingRequestFuelBooking(
            **validated_data,
            processed_by=request_person.fullname,
            handling_request=handling_request)
        fuel_booking.updated_by = request_person

        fuel_booking.handling_request.fuel_required_on = fuel_required_on
        fuel_booking.handling_request.fuel_quantity = fuel_quantity
        fuel_booking.handling_request.fuel_unit = fuel_unit
        fuel_booking.handling_request.fuel_prist_required = fuel_prist_required

        fuel_booking.save()

        return fuel_booking

    def update(self, fuel_booking, validated_data):
        request_person = getattr(self.context['request'].user, 'person')

        fuel_required_on = validated_data.pop('fuel_required_on', None)
        fuel_quantity = validated_data.pop('fuel_quantity', None)
        fuel_unit = validated_data.pop('fuel_unit_id', None)
        fuel_prist_required = validated_data.pop('fuel_prist_required', None)

        fuel_booking.updated_by = request_person
        fuel_booking.handling_request.fuel_required_on = fuel_required_on
        fuel_booking.handling_request.fuel_quantity = fuel_quantity
        fuel_booking.handling_request.fuel_unit = fuel_unit
        fuel_booking.handling_request.fuel_prist_required = fuel_prist_required

        fuel_booking = super().update(fuel_booking, validated_data)

        return fuel_booking


class HandlingRequestSerializer(serializers.ModelSerializer):
    """
    Serializer with the full representation of the S&F Request
    """
    aircraft_type = AircraftTypeSerializer()
    created_by = PersonSerializer()
    # TODO: 'customer_person' S&F Request filed deprecated
    customer_person = PersonSerializer(source='primary_contact')
    crew = HandlingRequestCrewSerializer(many=True, source='mission_crew')
    customer_organisation = OrganisationSerializer(read_only=True)
    airport = HandlingLocationSerializer()
    status = serializers.SerializerMethodField()
    spf_status = serializers.SerializerMethodField()
    booking_completed = serializers.SerializerMethodField()
    is_handling_request_sent = serializers.SerializerMethodField()
    is_aog_available = serializers.SerializerMethodField()
    handler = HandlerOrganisationSerializer(source='handling_agent')
    is_departure_editing_grace_period = serializers.SerializerMethodField()
    movement = HandlingRequestMovementSerializer(many=True)
    service_booking = serializers.IntegerField(write_only=True)
    movement_services_booking = serializers.IntegerField(write_only=True)
    booking_confirmed = serializers.BooleanField(write_only=True)
    available_handling_agents = serializers.SerializerMethodField(
        read_only=True,
    )
    available_arrival_services = serializers.SerializerMethodField()
    available_departure_services = serializers.SerializerMethodField()

    note_public = serializers.CharField(max_length=500, write_only=True, allow_blank=True)
    note_internal = serializers.CharField(max_length=500, write_only=True, allow_blank=True)
    spf = ServiceProvisionFormSerializer()
    ipa = OrganisationSerializer(source='fuel_booking.ipa', read_only=True)
    request_reference = serializers.SerializerMethodField()
    type = HandlingRequestTypeSerializer()
    air_card_prefix = AirCardPrefixSimpleSerializer(many=False, read_only=True)
    fuel_booking = FuelBookingSerializer(many=False, read_only=True)
    fuel_booking_confirmed = serializers.SerializerMethodField()
    fuel_booking_status = serializers.SerializerMethodField()
    fuel_dla_contract = FuelDlaContractSerializer(many=False, read_only=True)
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = HandlingRequest
        read_only_fields = ['fuel_booking_confirmed', 'is_handling_confirmed', 'is_pdf_available', 'is_standalone', ]
        fields = ['id', 'status', 'spf_status',
                  'booking_completed',

                  # Handling
                  'is_ground_handling_confirmation_applicable',
                  'is_ground_handling_request_can_be_sent', 'is_handling_request_sent', 'is_handling_confirmed',
                  'handler',

                  'is_standalone', 'is_pdf_available', 'is_departure_editing_grace_period', 'is_aog_available',
                  'tail_number', 'mission_number', 'callsign', 'request_reference', 'type',
                  'air_card_prefix', 'air_card_number', 'air_card_expiration', 'apacs_number',

                  # Fuel
                  'fuel_required', 'fuel_quantity', 'fuel_unit', 'fuel_prist_required',
                  'fuel_dla_contract', 'fuel_booking_confirmed', 'fuel_booking_status', 'fuel_booking',

                  'notify_dao', 'created_at',
                  'parking_apron', 'parking_stand', 'customer_organisation', 'crew',
                  'customer_person', 'created_by', 'airport', 'aircraft_type', 'ipa', 'handling_agent', 'movement',
                  'service_booking', 'movement_services_booking', 'booking_confirmed',
                  'available_handling_agents', 'is_services_editable', 'available_arrival_services',
                  'available_departure_services',
                  'note_public', 'note_internal', 'spf', 'conversation_id', ]

    def get_available_arrival_services(self, obj):
        movement_direction = MovementDirection.objects.get(pk='ARRIVAL')
        items = HandlingService.objects.dod_services(
            movement_direction=movement_direction,
            airport=obj.airport,
            handling_request=obj,
        ).prefetch_related('hs_availability')
        serializer = HandlingServiceSimpleSerializer(instance=items, many=True)
        return serializer.data

    def get_available_departure_services(self, obj):
        movement_direction = MovementDirection.objects.get(pk='DEPARTURE')
        items = HandlingService.objects.dod_services(
            movement_direction=movement_direction,
            airport=obj.airport,
            handling_request=obj,
        ).prefetch_related('hs_availability')
        serializer = HandlingServiceSimpleSerializer(instance=items, many=True)
        return serializer.data

    def get_status(self, obj):
        return obj.get_full_status

    def get_spf_status(self, obj):
        return obj.spf_status

    def get_fuel_booking_confirmed(self, obj):
        return obj.is_fuel_booking_confirmed

    def get_fuel_booking_status(self, obj):
        return obj.fuel_status

    def get_booking_completed(self, obj):
        return obj.booking_completed

    def get_is_handling_request_sent(self, obj):
        return hasattr(obj, 'auto_spf')

    def get_is_aog_available(self, obj):
        return getattr(obj, 'is_aog_available', None)

    def get_is_departure_editing_grace_period(self, obj):
        return getattr(obj, 'is_departure_editing_grace_period', False)

    def get_request_reference(self, obj):
        return obj.reference

    def get_conversation_id(self, obj):
        conversation = obj.chat_conversations.first()
        return conversation.pk if conversation else None

    def get_available_handling_agents(self, obj):
        '''
        Get Handling Agent objects available for the Handling Request airport
        '''
        items = Organisation.objects.handling_agent().filter(
            handler_details__airport=obj.airport).all()
        serializer = OrganisationSerializer(instance=items, many=True)
        return serializer.data

    def validate_handling_agent(self, value):
        '''
        Validate if the submitted Handling Agent provide services in the requested airport.
        '''
        handler_details = getattr(value, 'handler_details', None)
        if handler_details and handler_details.airport == self.instance.airport:
            return value
        else:
            raise serializers.ValidationError(
                detail='Handling Agent does not available in this airport')

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if 'service_booking' in attrs:
            if not self.instance.handling_agent and attrs[
                'booking_confirmed'] == True and not 'handling_agent' in attrs:
                raise serializers.ValidationError(
                    detail={'booking_confirmed': 'Handling Agent should be set to confirm service booking'})

        return validated_data

    def update(self, instance, validated_data):
        booking_confirmed = None
        service_booking = None
        movement_services_booking = None

        if 'booking_confirmed' in validated_data:
            booking_confirmed = validated_data.pop('booking_confirmed')

        if 'service_booking' in validated_data:
            service_booking = validated_data.pop('service_booking')

        if 'movement_services_booking' in validated_data:
            movement_services_booking = validated_data.pop('movement_services_booking')

        if booking_confirmed is not None and service_booking:
            handling_reqeust_service = HandlingRequestServices.objects.get(pk=service_booking)
            handling_reqeust_service.booking_confirmed = booking_confirmed

            if 'note_public' in validated_data:
                note_public = validated_data.pop('note_public')
                handling_reqeust_service.note = note_public

            if 'note_internal' in validated_data:
                note_internal = validated_data.pop('note_internal')
                handling_reqeust_service.note_internal = note_internal

            handling_reqeust_service.save()

        if booking_confirmed is not None and movement_services_booking:
            HandlingRequestServices.objects.filter(
                movement_id=movement_services_booking).update(booking_confirmed=booking_confirmed)

        instance.updated_by = self.context['request'].user.person
        instance = super().update(instance, validated_data)

        # Pull instance from database to re-calculate status
        instance = HandlingRequest.objects.with_status().get(pk=instance.pk)
        return instance


class HandlingRequestTailNumberSerializer(serializers.ModelSerializer):
    tail_number_id = RelatedFieldAlternative(required=True, write_only=True, source='tail_number',
                                             queryset=AircraftHistory.objects.all())

    class Meta:
        model = HandlingRequest
        fields = ['id', 'tail_number', 'tail_number_id', ]

    def update(self, handling_request, validated_data):
        tail_number = validated_data.get('tail_number', None)
        aircraft_type = getattr(tail_number.aircraft, 'type')

        if tail_number.operator != handling_request.customer_organisation:
            raise serializers.ValidationError(
                detail={'tail_number_id': ['Not applicable Tail Number']})

        handling_request.tail_number = tail_number
        handling_request.aircraft_type = aircraft_type
        handling_request.updated_by = self.context['request'].user.person
        handling_request = super().update(handling_request, validated_data)
        return handling_request


class HandlingRequestAirCardSerializer(serializers.ModelSerializer):
    air_card_prefix = AirCardPrefixSimpleSerializer(read_only=True)
    air_card_prefix_id = RelatedFieldAlternative(required=True, write_only=True, source='air_card_prefix',
                                                 queryset=AirCardPrefix.objects.all())

    class Meta:
        model = HandlingRequest
        fields = ['id', 'air_card_prefix_id', 'air_card_prefix', 'air_card_number', 'air_card_expiration', ]

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if 'air_card_expiration' in validated_data:
            air_card_expiration = validated_data.get('air_card_expiration')
            validation_result = aircard_expiration_validation(air_card_expiration=air_card_expiration)
            if not validation_result:
                raise serializers.ValidationError(
                    detail={'air_card_expiration': 'AIR Card expired'})

        return validated_data

    def update(self, instance, validated_data):
        instance.updated_by = self.context['request'].user.person
        instance = super().update(instance, validated_data)
        return instance


class HandlingRequestUpdateMissionTypeSerializer(serializers.ModelSerializer):
    type = HandlingRequestTypeSerializer(read_only=True)
    type_id = RelatedFieldAlternative(required=True, write_only=True, source='type',
                                      queryset=HandlingRequestType.objects.all())

    class Meta:
        model = HandlingRequest
        fields = ['id', 'type_id', 'type', ]

    def update(self, instance, validated_data):
        instance.updated_by = self.context['request'].user.person
        instance = super().update(instance, validated_data)
        return instance


class FuelBookingIpaSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSerializer(read_only=True)
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'name', ]

    def create(self, validated_data, *args, **kwargs):
        request_user = getattr(self.context['request'], 'user')
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        ipa_name = validated_data.get('name')

        # Check existing IPA by name
        existing_ipa = Organisation.objects.fuelling_ipa_or_handler().filter(details__registered_name=ipa_name).first()
        if existing_ipa:
            if not existing_ipa.ipa_locations.filter(pk=handling_request.airport.pk).exists():
                raise serializers.ValidationError(
                    detail={'name': ["This IPA already exists but not provide servicing in S&F Request airport"]},
                    code='invalid_value')
            return existing_ipa

        organisation_details = OrganisationDetails.objects.create(
            registered_name=ipa_name,
            type_id=4,
            country=handling_request.airport.airport_details.region.country,
            updated_by=request_user,
        )

        organisation = Organisation.objects.create(details=organisation_details)

        organisation_details.organisation = organisation
        organisation_details.save()

        organisation.ipa_locations.set([handling_request.airport])
        ipa_details = IpaDetails.objects.create(
            organisation=organisation,
        )
        organisation_restricted = OrganisationRestricted.objects.create(
            organisation=organisation,
            is_service_supplier=True
        )

        return organisation


class HandlingRequestHandlerSerializer(serializers.ModelSerializer):
    details = OrganisationDetailsSerializer(read_only=True)
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Organisation
        fields = ['id', 'details', 'name', ]

    def create(self, validated_data, *args, **kwargs):
        request_user = getattr(self.context['request'], 'user')
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        handler_name = validated_data.get('name')

        # Check existing Handler by name
        existing = Organisation.objects.handling_agent().filter(details__registered_name=handler_name).first()
        if existing:
            if existing.handler_details.airport != handling_request.airport:
                raise serializers.ValidationError(
                    detail={'name': ["This Handler already exists but not provide servicing in S&F Request airport"]},
                    code='invalid_value')
            return existing

        organisation_details = OrganisationDetails.objects.create(
            registered_name=handler_name,
            type_id=3,
            country=handling_request.airport.airport_details.region.country,
            updated_by=request_user,
        )

        organisation = Organisation.objects.create(details=organisation_details)

        organisation_details.organisation = organisation
        organisation_details.save()

        handler_details, created = HandlerDetails.objects.update_or_create(
            organisation=organisation,
            airport=handling_request.airport,
            handles_military=True,
            handler_type_id=8,
        )

        organisation_restricted = OrganisationRestricted.objects.create(
            organisation=organisation,
            is_service_supplier=True
        )

        return organisation


class HandlingRequestPPRUpdateSerializer(serializers.ModelSerializer):
    arrival_ppr_number = serializers.CharField(required=False, write_only=True)
    departure_ppr_number = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = HandlingRequest
        fields = ['id', 'arrival_ppr_number', 'departure_ppr_number', ]

    def update(self, handling_request, validated_data):
        arrival_ppr_number = validated_data.pop('arrival_ppr_number', None)
        departure_ppr_number = validated_data.pop('departure_ppr_number', None)
        request_person = getattr(self.context['request'].user, 'person')

        if arrival_ppr_number:
            arrival_movement = handling_request.arrival_movement
            arrival_movement.updated_by = request_person
            arrival_movement.ppr_number = arrival_ppr_number
            arrival_movement.save()

        if departure_ppr_number:
            departure_movement = handling_request.departure_movement
            departure_movement.updated_by = request_person
            departure_movement.ppr_number = departure_ppr_number
            departure_movement.save()

        handling_request.updated_by = request_person
        handling_request = super().update(handling_request, validated_data)
        return handling_request


class HandlingRequestUnableToSupportSerializer(serializers.ModelSerializer):
    handling_agent_id = RelatedFieldAlternative(required=True, write_only=True, source='handling_agent',
                                                queryset=Organisation.objects.handling_agent())

    class Meta:
        model = HandlingRequest
        fields = ['id', 'decline_reason', 'handling_agent_id', ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        handling_request = HandlingRequest.objects.with_status().get(pk=instance.pk)
        serializer = HandlingRequestSerializer(instance=handling_request, many=False)
        return serializer.data

    def update(self, instance, validated_data):
        request_user = getattr(self.context['request'], 'user')

        instance.is_unable_to_support = True
        instance = super().update(instance, validated_data)

        unable_to_support_actions(
            handling_request=instance,
            author=getattr(request_user, 'person', None),
        )

        return instance


class SendHandlingRequestSerializer(serializers.ModelSerializer):
    mark_as_sent = serializers.BooleanField(required=False, write_only=True)
    handler_email = serializers.ListField(required=False, write_only=True)
    send_to_people = serializers.ListField(required=False, write_only=True)

    class Meta:
        model = HandlingRequest
        fields = ['id', 'mark_as_sent', 'handler_email', 'send_to_people', ]

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        mark_as_sent = validated_data.get('mark_as_sent')

        handler_email_addresses = self.instance.handling_agent.get_email_address()
        if not handler_email_addresses and not mark_as_sent:
            handler_email = validated_data.get('handler_email')
            if not handler_email:
                raise serializers.ValidationError(
                    detail={'handler_email': 'Ground Handler has no contact email address stored. Please enter the '
                                             'email address that the ground handling request should be sent to (this '
                                             'will be stored for future use)'})

        return validated_data

    def update(self, instance, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        mark_as_sent = validated_data.pop('mark_as_sent', None)
        send_to_people_emails = validated_data.pop('send_to_people', [])
        handler_email = validated_data.pop('handler_email', [])
        final_cc_list = []

        instance.is_new = False
        instance.amended = False
        instance.updated_by = request_person
        instance = super().update(instance, validated_data)

        with transaction.atomic():
            handler_email_addresses = instance.handling_agent.get_email_address()

            # Update S&F Request Handler with given email address
            if not handler_email_addresses and handler_email:
                handler_details = getattr(instance.handling_agent, 'handler_details')
                handler_details.contact_email = handler_email.pop(0)
                handler_details.save()

            AutoServiceProvisionForm.objects.create(
                handling_request=instance,
                sent_to=instance.handling_agent,
            )

            # Send AutoSPF to Handler
            final_cc_list += handler_email
            final_cc_list += send_to_people_emails

            if not mark_as_sent:
                generate_auto_spf_email.delay(
                    handling_request_id=instance.pk,
                    requester_person_id=request_person.pk,
                    addresses_cc=final_cc_list,
                )

                instance.activity_log.create(
                    author=request_person,
                    record_slug='sfr_ground_handling_submitted',
                    details='Handling Request: Submitted',
                )
            else:
                instance.activity_log.create(
                    author=request_person,
                    record_slug='sfr_ground_handling_submitted',
                    details='Handling Request: Sent Externally',
                )

        return instance


class HandlingRequestGroundHandlingConfirmationSerializer(serializers.ModelSerializer):
    confirm_all_services = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = HandlingRequest
        fields = ['id', 'confirm_all_services', ]

    def update(self, handling_request, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        handling_request.updated_by = request_person
        handling_request.is_handling_confirmed = True
        handling_request.confirm_handling_services = validated_data.pop('confirm_all_services', None)
        handling_request = super().update(handling_request, validated_data)
        return handling_request
