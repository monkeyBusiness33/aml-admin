from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, exceptions

from aircraft.models import AircraftType, AircraftHistory
from api.serializers.aircraft import AircraftTypeSerializer, TailNumberSerializer
from api.serializers.core import UnitOfMeasurementSerializer, AirCardPrefixSimpleSerializer
from api.serializers.handling_admin import HandlingRequestTypeSerializer
from api.serializers.handling_base import HandlingLocationSerializer
from api.serializers.organisation import OrganisationSerializer
from api.serializers.user import PersonSerializer
from api.utils.related_field import RelatedFieldAlternative
from core.models import UnitOfMeasurement, AirCardPrefix
from core.utils.validators import aircard_number_validation_simple, aircard_expiration_validation
from handling.models import HandlingRequestType, HandlingService, HandlingRequest
from handling.serializers import HandlingServiceSerializer
from mission.models import Mission, MissionLeg
from mission.models.mission import MissionTurnaround, MissionTurnaroundService, MissionLegCancellationReason
from mission.utils.legs_utils import mission_legs_cancel, mission_legs_update_consistency, mission_leg_amend_timings
from organisation.models import Organisation
from user.models import Person


class MissionLegCancellationReasonSerializer(serializers.ModelSerializer):

    class Meta:
        model = MissionLegCancellationReason
        fields = [
            'id', 'name',
        ]


class MissionTurnaroundHandlingRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = HandlingRequest
        fields = [
            'id',
        ]


class TurnaroundServicesListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.order_by('id')
        return super().to_representation(data)


class MissionTurnaroundServiceSerializer(serializers.ModelSerializer):
    service = RelatedFieldAlternative(queryset=HandlingService.objects.all(),
                                      serializer=HandlingServiceSerializer)

    class Meta:
        model = MissionTurnaroundService
        list_serializer_class = TurnaroundServicesListSerializer
        fields = [
            'id',
            'on_arrival',
            'on_departure',
            'booking_text',
            'booking_quantity',
            'note',
            'service',
        ]


class MissionTurnaroundSerializer(serializers.ModelSerializer):
    fuel_unit = RelatedFieldAlternative(queryset=UnitOfMeasurement.objects.all(),
                                        serializer=UnitOfMeasurementSerializer, required=False, allow_null=True)
    services = MissionTurnaroundServiceSerializer(many=True, source='requested_services')
    fuel_booking_status = serializers.SerializerMethodField()
    gh_booking_status = serializers.SerializerMethodField()
    handling_request = MissionTurnaroundHandlingRequestSerializer(many=False, read_only=True)

    class Meta:
        model = MissionTurnaround
        fields = [
            'fuel_required',
            'fuel_quantity',
            'fuel_unit',
            'fuel_prist_required',
            'fuel_booking_status',
            'gh_booking_status',
            'handling_request',
            'services',
        ]

    def get_fuel_booking_status(self, obj):  # noqa
        if not obj.handling_request:
            return None
        return obj.handling_request.fuel_status

    def get_gh_booking_status(self, obj):  # noqa
        if not obj.handling_request:
            return None
        return obj.handling_request.ground_handling_status


class MissionLegsListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(is_cancelled=False)
        return super().to_representation(data)


class MissionLegSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    departure_location = RelatedFieldAlternative(queryset=Organisation.objects.all(),
                                                 serializer=HandlingLocationSerializer)
    departure_ppr = serializers.SerializerMethodField()
    departure_datetime_is_local = serializers.BooleanField(write_only=True, default=False)
    arrival_location = RelatedFieldAlternative(queryset=Organisation.objects.all(),
                                               serializer=HandlingLocationSerializer)
    arrival_ppr = serializers.SerializerMethodField()
    arrival_datetime_is_local = serializers.BooleanField(write_only=True, default=False)
    servicing = MissionTurnaroundSerializer(required=False, source='turnaround')

    class Meta:
        model = MissionLeg
        list_serializer_class = MissionLegsListSerializer
        fields = [
            'id',
            'sequence_id',
            'departure_location', 'departure_datetime', 'departure_diplomatic_clearance', 'departure_aml_service',
            'departure_ppr', 'departure_datetime_is_local',

            'arrival_location', 'arrival_datetime', 'arrival_diplomatic_clearance', 'arrival_aml_service',
            'arrival_ppr', 'arrival_datetime_is_local',

            'pob_crew', 'pob_pax', 'cob_lbs', 'callsign_override',
            'servicing',
        ]

    def get_departure_ppr(self, obj): # noqa
        return None

    def get_arrival_ppr(self, obj): # noqa
        return None

    def to_representation(self, mission_leg):
        data = super().to_representation(mission_leg)
        # Need to return null value instead empty object for correct behaviour of the Mission Create/Edit page
        if not mission_leg.arrival_aml_service:
            data['servicing'] = None
        return data


class MissionSerializer(serializers.ModelSerializer):
    legs = MissionLegSerializer(many=True)
    type = RelatedFieldAlternative(queryset=HandlingRequestType.objects.all(), serializer=HandlingRequestTypeSerializer)
    organisation = RelatedFieldAlternative(queryset=Organisation.objects.all(),
                                           serializer=OrganisationSerializer)
    requesting_person = RelatedFieldAlternative(queryset=Person.objects.all(),
                                                serializer=PersonSerializer)
    mission_planner = RelatedFieldAlternative(queryset=Person.objects.all(),
                                              serializer=PersonSerializer,
                                              allow_null=True, required=False)
    aircraft_type = RelatedFieldAlternative(queryset=AircraftType.objects.all(), serializer=AircraftTypeSerializer)
    aircraft = RelatedFieldAlternative(queryset=AircraftHistory.objects.all(), serializer=TailNumberSerializer,
                                       allow_null=True, required=False)
    conversation_id = serializers.SerializerMethodField()
    air_card_prefix = AirCardPrefixSimpleSerializer(many=False, required=False, allow_null=True, read_only=True)

    class Meta:
        model = Mission

        fields = [
            'id',
            'mission_number_prefix',
            'mission_number',
            'type',
            'callsign',
            'conversation_id',
            'start_date',
            'end_date',
            'air_card_prefix',
            'air_card_number',
            'air_card_expiration',
            'air_card_photo',
            'status',
            'organisation',
            'requesting_person',
            'mission_planner',
            'aircraft_type',
            'aircraft',
            'apacs_number',
            'apacs_url',
            'legs',
        ]
        read_only_fields = [
            'air_card_prefix', 'air_card_number', 'air_card_expiration', 'air_card_photo',
        ]

    def get_conversation_id(self, obj):  # noqa
        return obj.conversation_id

    def validate(self, data):
        request_person = getattr(self.context['request'].user, 'person')

        # Force person primary organisation in case of non staff user
        if not request_person.is_aml_staff:
            data['organisation'] = request_person.primary_dod_position.organisation

        return data

    def update(self, mission, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        mission_legs_validated_data = validated_data.pop('legs')

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(mission, attr, value)
            mission.updated_by = request_person
            mission.meta_is_partial_save = True
            mission.save()

            mission_legs_sorted = sorted(mission_legs_validated_data, key=lambda d: d['sequence_id'])

            # Cancel Flight legs which does no more exists in payload
            remaining_flight_legs_ids = [i['id'] for i in mission_legs_sorted if 'id' in i]
            flight_leg_to_cancel = mission.active_legs.filter(~Q(pk__in=remaining_flight_legs_ids))
            for flight_leg_to_cancel in flight_leg_to_cancel:
                flight_leg_to_cancel.updated_by = request_person
                mission_legs_cancel(mission_leg=flight_leg_to_cancel)

            # Update remaining Flight Legs
            for mission_leg_data in mission_legs_sorted:
                leg_id = mission_leg_data.get('id')
                is_current_leg_last_in_list = mission_leg_data == mission_legs_sorted[-1]

                departure_datetime_is_local = mission_leg_data.pop('departure_datetime_is_local', None)
                arrival_datetime_is_local = mission_leg_data.pop('arrival_datetime_is_local', None)
                turnaround_data = mission_leg_data.pop('turnaround', None)

                mission_leg = mission.legs.filter(pk=leg_id).first()
                if mission_leg:
                    for attr, value in mission_leg_data.items():
                        setattr(mission_leg, attr, value)

                    # Disable servicing and remove Turnaround for last leg if it exists
                    if is_current_leg_last_in_list:
                        mission_leg.arrival_aml_service = False

                    mission_leg.prevent_mission_update = True
                    mission_leg.departure_datetime_is_local = departure_datetime_is_local
                    mission_leg.arrival_datetime_is_local = arrival_datetime_is_local
                    mission_leg.updated_by = request_person
                    mission_leg.save()
                else:
                    mission_leg_id = mission_leg_data.get('id')
                    if mission_leg_id:
                        raise serializers.ValidationError(
                            "You trying to update Mission Leg which does not corresponds to the current Mission")
                    mission_leg = MissionLeg(
                        **mission_leg_data,
                        mission=mission,
                        created_by=request_person,
                    )
                    mission_leg.prevent_mission_update = True
                    mission_leg.departure_datetime_is_local = departure_datetime_is_local
                    mission_leg.arrival_datetime_is_local = arrival_datetime_is_local
                    mission_leg.updated_by = request_person
                    mission_leg.save()

                # Turnaround and servicing processing
                if is_current_leg_last_in_list:
                    # Remove Turnaround for last mission leg
                    MissionTurnaround.objects.filter(mission_leg=mission_leg).delete()
                elif not mission_leg.arrival_aml_service:
                    # Create empty Turnaround for a MissionLeg
                    mission_turnaround, created = MissionTurnaround.objects.update_or_create(
                        mission_leg=mission_leg,
                        defaults={
                            'fuel_required': None,
                            'fuel_quantity': None,
                            'fuel_unit': None,
                            'fuel_prist_required': False,

                        }
                    )
                    MissionTurnaroundService.objects.filter(turnaround=mission_turnaround).delete()
                else:
                    if not turnaround_data:
                        raise serializers.ValidationError("Servicing is requested but no details submitted")
                    turnaround_services_data = turnaround_data.pop('requested_services', None)

                    turnaround, created = MissionTurnaround.objects.update_or_create(
                        mission_leg=mission_leg,
                        defaults={**turnaround_data}
                    )
                    requested_services_ids = []
                    # Create or update requested services
                    for service_data in turnaround_services_data:
                        requested_services_ids.append(service_data['service'])
                        turnaround.requested_services.update_or_create(
                            service=service_data['service'],
                            defaults={
                                'updated_by': request_person,
                                **service_data,
                            },
                        )

                    # Cleanup not requested services
                    services_to_remove = turnaround.requested_services.exclude(service__in=requested_services_ids)
                    for service in services_to_remove:
                        service.updated_by = request_person
                        service.delete()

            mission_legs_update_consistency(mission=mission)

        mission.meta_is_partial_save = False
        mission.save()
        return mission

    def create(self, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        mission_legs_validated_data = validated_data.pop('legs')

        with transaction.atomic():
            # Create Mission
            mission = Mission(
                **validated_data,
                created_by=request_person,
            )
            mission.updated_by = request_person
            mission.meta_is_partial_save = True
            mission.save()

            # Create MissionLeg set
            mission_legs = []
            previous_leg = None
            mission_legs_sorted = sorted(mission_legs_validated_data, key=lambda d: d['sequence_id'])
            for mission_leg_data in mission_legs_validated_data:
                is_current_leg_last_in_list = mission_leg_data == mission_legs_sorted[-1]
                departure_datetime_is_local = mission_leg_data.pop('departure_datetime_is_local', None)
                arrival_datetime_is_local = mission_leg_data.pop('arrival_datetime_is_local', None)
                turnaround_data = mission_leg_data.pop('turnaround', None)

                mission_leg = MissionLeg(
                    **mission_leg_data,
                    previous_leg=previous_leg,
                    mission=mission,
                    created_by=request_person,

                )
                mission_leg.departure_datetime_is_local = departure_datetime_is_local
                mission_leg.arrival_datetime_is_local = arrival_datetime_is_local
                mission_leg.updated_by = request_person
                mission_leg.prevent_mission_update = True
                mission_leg.save()

                # Validation steps
                if mission_leg.previous_leg:
                    if mission_leg.departure_datetime < mission_leg.previous_leg.arrival_datetime:
                        raise serializers.ValidationError(
                            "Flight Leg departure time should be greater than arrival time of previous Leg")
                    if mission_leg.departure_location != mission_leg.previous_leg.arrival_location:
                        raise serializers.ValidationError(
                            "Flight Leg departure location should be the same as arrival location of previous Leg")

                previous_leg = mission_leg
                mission_legs.append(mission_leg)

                # Create empty Turnaround for a MissionLeg (excluding last FlightLeg)
                if not mission_leg.arrival_aml_service and not is_current_leg_last_in_list:

                    MissionTurnaround.objects.update_or_create(
                        mission_leg=mission_leg,
                        defaults={
                            'fuel_required': None,
                            'fuel_quantity': None,
                            'fuel_unit': None,
                            'fuel_prist_required': False,

                        }
                    )

                if mission_leg.arrival_aml_service:
                    if not turnaround_data:
                        raise serializers.ValidationError("Servicing is requested but no details submitted")
                    turnaround_services_data = turnaround_data.pop('requested_services', None)

                    turnaround = MissionTurnaround.objects.create(
                        mission_leg=mission_leg,
                        **turnaround_data,
                    )
                    for service_data in turnaround_services_data:
                        turnaround.requested_services.create(
                            updated_by=request_person,
                            **service_data)

        mission.meta_is_partial_save = False
        mission.save()

        return mission


class MissionListSerializer(serializers.ModelSerializer):
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    mission_number = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id',
            'mission_number',
            'callsign',
            'start_date',
            'end_date',
            'status',
        ]

    def get_mission_number(self, obj):  # noqa
        return obj.mission_number_repr

    def get_start_date(self, obj):  # noqa
        return obj.start_date

    def get_end_date(self, obj):  # noqa
        return obj.end_date


class MissionLegCancelSerializer(serializers.ModelSerializer):
    cancel_subsequent_legs = serializers.BooleanField(required=False)
    cancellation_reason = RelatedFieldAlternative(queryset=MissionLegCancellationReason.objects.all(),
                                                  serializer=MissionLegCancellationReasonSerializer,
                                                  required=False)

    class Meta:
        model = MissionLeg
        fields = [
            'id',
            'cancel_subsequent_legs',
            'cancellation_reason',
        ]

    def update(self, mission_leg, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        cancel_subsequent_legs = validated_data.get('cancel_subsequent_legs')
        cancellation_reason = validated_data.get('cancellation_reason')
        mission_leg.updated_by = request_person
        mission_legs_cancel(mission_leg=mission_leg,
                            cancellation_reason_id=cancellation_reason.pk if cancellation_reason else None,
                            cancel_subsequent_legs=cancel_subsequent_legs)

        return mission_leg

    def to_representation(self, mission_leg):
        mission = Mission.objects.get(pk=mission_leg.mission.pk)
        serializer = MissionSerializer(mission, many=False)
        return serializer.data


class MissionLegDelaySerializer(serializers.ModelSerializer):
    apply_to_subsequent_legs = serializers.BooleanField(required=False)

    class Meta:
        model = MissionLeg
        fields = [
            'id',
            'departure_datetime',
            'apply_to_subsequent_legs',
        ]

    def update(self, mission_leg, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        departure_date = validated_data.get('departure_datetime')
        apply_to_subsequent_legs = validated_data.get('apply_to_subsequent_legs')

        # Validations
        if not departure_date:
            raise serializers.ValidationError(detail='Please submit new departure date')
        if departure_date < timezone.now():
            raise serializers.ValidationError(detail='New date cant be in past')

        previous_leg = getattr(mission_leg, 'previous_leg', None)
        if previous_leg and departure_date <= previous_leg.arrival_datetime:
            raise serializers.ValidationError(detail='New date cant be earlier than previous Flight Leg Arrival')

        # Calculate difference between current datetime and new
        delta = departure_date - mission_leg.departure_datetime

        # Validate overlap
        overlapped_missions = mission_leg.validate_overlap()
        if overlapped_missions:
            overlapped_mission = overlapped_missions.first()
            raise serializers.ValidationError(
                detail=f'The delayed arrival movement for flight leg {mission_leg.sequence_id} overlaps the '
                       f'departure movement for flight {overlapped_mission.sequence_id}. Please first amend '
                       f'the departure movement for leg {overlapped_mission.sequence_id} before delaying this movement')

        try:
            mission_leg = mission_leg_amend_timings(mission_leg=mission_leg,
                                                    delta=delta,
                                                    updated_by=request_person,
                                                    roll_change_to_subsequent_legs=apply_to_subsequent_legs,
                                                    )
        except ValidationError as validation_error:
            raise serializers.ValidationError(validation_error)

        return mission_leg

    def to_representation(self, mission_leg):
        mission = Mission.objects.get(pk=mission_leg.mission.pk)
        serializer = MissionSerializer(mission, many=False)
        return serializer.data


class MissionsSetAirCardSerializer(serializers.Serializer):
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
        missions_by_callsign_qs = person_position.get_missions_list().filter(
            callsign=validated_data.get('callsign'),
        )

        # Update Missions
        if missions_by_callsign_qs.exists():
            if air_card_photo:
                from django.core.files.base import ContentFile
                air_card_photo_file = ContentFile(air_card_photo.read(), 'air_card_photo.png')

            for mission in missions_by_callsign_qs:
                if air_card_photo:
                    air_card_photo_file.name = f'aircard_photo_mission_{mission.pk}_{mission.callsign}.png'
                    mission.air_card_photo = air_card_photo_file

                air_card_prefix_id = validated_data.get('air_card_prefix_id')
                air_card_prefix = AirCardPrefix.objects.filter(pk=air_card_prefix_id).first()

                mission.air_card_prefix = air_card_prefix
                mission.air_card_number = validated_data.get('air_card_number')
                mission.air_card_expiration = validated_data.get('air_card_expiration')
                mission.save()

                mission.activity_log.create(
                    details=f'AIR Card details has been submitted',
                    author=request_person,
                )
        else:
            raise exceptions.NotFound(
                detail='No Handling Request with provided callsign', code='not_found')
        return missions_by_callsign_qs.first()


class AirCardValidationMixin(serializers.Serializer):
    air_card_prefix = RelatedFieldAlternative(queryset=AirCardPrefix.objects.all(),
                                              serializer=AirCardPrefixSimpleSerializer,
                                              )

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if 'air_card_expiration' in validated_data:
            air_card_expiration = validated_data.get('air_card_expiration')
            validation_result = aircard_expiration_validation(air_card_expiration=air_card_expiration)
            if not validation_result:
                raise serializers.ValidationError(
                    detail={'air_card_expiration': 'AIR Card expired'})

        return validated_data


class MissionAirCardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Mission
        fields = ['id', 'air_card_prefix', 'air_card_number', 'air_card_expiration', ]
        extra_kwargs = {'air_card_number': {'required': True}, 'air_card_expiration': {'required': True}}

    def update(self, mission, validated_data):
        mission.updated_by = self.context['request'].user.person
        mission = super().update(mission, validated_data)
        return mission


class MissionLegAirCardSerializer(serializers.ModelSerializer, AirCardValidationMixin):

    class Meta:
        model = MissionLeg
        fields = ['id', 'air_card_prefix', 'air_card_number', 'air_card_expiration', ]
        extra_kwargs = {'air_card_number': {'required': True}, 'air_card_expiration': {'required': True}}

    def update(self, mission_leg, validated_data):
        mission_leg.updated_by = self.context['request'].user.person
        mission_leg = super().update(mission_leg, validated_data)
        return mission_leg


class MissionLegAmendTimingsSerializer(serializers.ModelSerializer):
    movement_direction = serializers.CharField(write_only=True)
    new_datetime = serializers.DateTimeField(write_only=True)
    roll_change_to_subsequent_legs = serializers.BooleanField(write_only=True)

    class Meta:
        model = MissionLeg
        fields = [
            'id',
            'movement_direction',
            'new_datetime',
            'roll_change_to_subsequent_legs',
        ]

    def update(self, mission_leg, validated_data):
        request_person = self.context['request'].user.person

        movement_direction = validated_data.get('movement_direction')
        new_datetime = validated_data.get('new_datetime')
        roll_change_to_subsequent_legs = validated_data.get('roll_change_to_subsequent_legs')

        if movement_direction == 'arrival':
            new_datetime_delta = new_datetime - mission_leg.arrival_datetime
        elif movement_direction == 'departure':
            new_datetime_delta = new_datetime - mission_leg.departure_datetime
        else:
            raise serializers.ValidationError("Unknown Movement Slug")

        # Run validation
        try:
            mission_leg_amend_timings(mission_leg=mission_leg,
                                      delta=new_datetime_delta,
                                      updated_by=request_person,
                                      roll_change_to_subsequent_legs=roll_change_to_subsequent_legs,
                                      commit=False,
                                      )
        except ValidationError as validation_error:
            raise serializers.ValidationError(list(validation_error)[0])

        # Write data
        mission_leg_amend_timings(mission_leg=mission_leg,
                                  delta=new_datetime_delta,
                                  updated_by=request_person,
                                  roll_change_to_subsequent_legs=roll_change_to_subsequent_legs,
                                  commit=True,
                                  )

        return mission_leg


class MissionGroundServicingTurnaroundServiceSerializer(serializers.ModelSerializer):
    service = RelatedFieldAlternative(queryset=HandlingService.objects.all(),
                                      serializer=HandlingServiceSerializer)
    is_deletable = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MissionTurnaroundService
        list_serializer_class = TurnaroundServicesListSerializer
        fields = [
            'id',
            'on_arrival',
            'on_departure',
            'booking_text',
            'booking_quantity',
            'note',
            'is_deletable',
            'service',
        ]

    def get_is_deletable(self, obj):  # noqa
        if obj.service.codename == 'passengers_handling':
            if obj.turnaround.mission_leg.mission.active_legs.filter(pob_pax__isnull=False).exists():
                return False
        if obj.service.codename == 'cargo_loading_unloading':
            if obj.turnaround.mission_leg.mission.active_legs.filter(cob_lbs__isnull=False).exists():
                return False
        return True


class MissionGroundServicingSerializer(serializers.ModelSerializer):
    services = MissionGroundServicingTurnaroundServiceSerializer(many=True, read_only=True, source='requested_services')
    updated_services = serializers.ListField(write_only=True)
    is_servicing_requested = serializers.SerializerMethodField(read_only=True)
    location = HandlingLocationSerializer(many=False, read_only=True, source='mission_leg.arrival_location')

    class Meta:
        model = MissionTurnaround
        fields = [
            'id',
            'is_servicing_requested',
            'location',
            'services',
            'updated_services',
        ]

    def get_is_servicing_requested(self, obj):  # noqa
        return obj.mission_leg.arrival_aml_service

    def update(self, mission, validated_data):
        request_person = getattr(self.context['request'].user, 'person')
        services = validated_data.get('updated_services')

        for service in services:
            service_obj = HandlingService.objects.get(pk=service['id'])
            is_deleted = service.get('is_deleted')

            if is_deleted:
                services_to_delete = MissionTurnaroundService.objects.filter(
                    turnaround__mission_leg__mission=mission,
                    service=service_obj
                )
                for turnaround_service in services_to_delete:
                    turnaround_service.updated_by = request_person
                    turnaround_service.delete()
            else:
                for turnaround in service['turnarounds']:
                    MissionTurnaroundService.objects.update_or_create(
                        turnaround_id=turnaround['id'],
                        service=service_obj,
                        defaults={
                            'on_arrival': turnaround['on_arrival'],
                            'on_departure': turnaround['on_departure'],
                            'booking_text': turnaround.get('booking_text'),
                            'booking_quantity': turnaround.get('booking_quantity'),
                            'note': turnaround.get('note'),
                            'updated_by': request_person,
                        },
                    )

        # Cleanup services which have no any checkbox set
        services_to_remove = MissionTurnaroundService.objects.filter(
            turnaround__mission_leg__mission=mission,
            on_arrival=False,
            on_departure=False,
        )
        for turnaround_service in services_to_remove:
            turnaround_service.updated_by = request_person
            turnaround_service.delete()

        return True
