from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, F

from handling.utils.localtime import get_utc_from_airport_local_time
from mission.utils.mission_leg_automatic_services import mission_leg_passengers_handling_service


def mission_leg_pre_save(mission_leg):
    # Prevent '' value for callsign, only NULL
    if mission_leg.callsign_override == '':
        mission_leg.callsign_override = None

    if mission_leg.callsign_override:
        mission_leg.callsign_override = mission_leg.callsign_override.replace(" ", "").upper()

    # Prevent '' value for diplomatic clearance, only NULL
    if mission_leg.departure_diplomatic_clearance == '':
        mission_leg.departure_diplomatic_clearance = None
    if mission_leg.arrival_diplomatic_clearance == '':
        mission_leg.arrival_diplomatic_clearance = None

    if hasattr(mission_leg, 'departure_datetime_is_local') and mission_leg.departure_datetime_is_local:
        mission_leg.departure_datetime = get_utc_from_airport_local_time(
            mission_leg.departure_datetime, mission_leg.departure_location)

    if hasattr(mission_leg, 'arrival_datetime_is_local') and mission_leg.arrival_datetime_is_local:
        mission_leg.arrival_datetime = get_utc_from_airport_local_time(
            mission_leg.arrival_datetime, mission_leg.arrival_location)

    return mission_leg


def mission_leg_after_save(mission_leg):
    author = getattr(mission_leg, 'updated_by', None)
    mission_leg_passengers_handling_service(mission_leg=mission_leg, author=author)

    if hasattr(mission_leg, 'is_created'):
        defaults = {
            'mission': mission_leg.mission,
            'person': mission_leg.mission.requesting_person,
            'is_primary_contact': True,
            'can_update_mission': True,
        }
        crew_position, created = mission_leg.mission.mission_crew_positions.get_or_create(**defaults)
        mission_leg.crew.update_or_create(crew_position=crew_position)

    if {'aircraft_type_override_id', 'aircraft_override_id'}.intersection(mission_leg.changed_fields):
        propagate_aircraft_update = getattr(mission_leg, 'propagate_aircraft_update', False)
        if propagate_aircraft_update:
            for flight_leg in mission_leg.mission.active_legs.filter(sequence_id__gt=mission_leg.sequence_id):
                flight_leg.aircraft_type_override = mission_leg.aircraft_type_override
                flight_leg.aircraft_override = mission_leg.aircraft_override
                flight_leg.prevent_mission_update = True
                flight_leg.updated_by = mission_leg.updated_by
                flight_leg.save()
    return mission_leg


def mission_legs_cancel(mission_leg, cancellation_reason_id=4, cancel_subsequent_legs=False):
    # Function to cancel Mission Leg(s)
    if cancel_subsequent_legs:
        q = Q(sequence_id__gte=mission_leg.sequence_id)
    else:
        q = Q(pk=mission_leg.pk)

    legs_to_cancel = mission_leg.mission.legs.filter(q)

    for leg_to_cancel in legs_to_cancel:
        leg_to_cancel.is_cancelled = True
        leg_to_cancel.previous_leg = None
        leg_to_cancel.updated_by = mission_leg.updated_by
        leg_to_cancel.cancellation_reason_id = cancellation_reason_id
        leg_to_cancel.prevent_mission_update = True
        leg_to_cancel.save()

        leg_to_cancel.activity_log.create(
            mission=leg_to_cancel.mission,
            record_slug=f'mission_leg_cancellation',
            author=mission_leg.updated_by,
        )

    mission_legs_enumerate(mission=mission_leg.mission)
    mission_legs_update_consistency(mission=mission_leg.mission)

    mission_leg.mission.updated_by = mission_leg.updated_by
    mission_leg.mission.save()

    return


def mission_leg_amend_timings(mission_leg, delta, updated_by, roll_change_to_subsequent_legs=False, commit=True):
    mission_leg = mission_leg.mission.active_legs.filter(pk=mission_leg.pk).first()
    mission_leg.departure_datetime = mission_leg.departure_datetime + delta
    mission_leg.arrival_datetime = mission_leg.arrival_datetime + delta

    is_conflict_with_previous_legs_qs = mission_leg.mission.active_legs.filter(
        sequence_id__lt=mission_leg.sequence_id,
        arrival_datetime__gte=mission_leg.departure_datetime,
    )

    # Validation
    validation_error_text = "New Date & Time overlaps another Flight Leg: "

    if is_conflict_with_previous_legs_qs.exists():
        validation_error = ', '.join([x.__str__() for x in is_conflict_with_previous_legs_qs])
        raise ValidationError(validation_error_text + validation_error)

    if not roll_change_to_subsequent_legs:
        is_conflict_with_next_legs_qs = mission_leg.mission.active_legs.filter(
            sequence_id__gt=mission_leg.sequence_id,
            arrival_datetime__lte=mission_leg.arrival_datetime,
        )
        if is_conflict_with_next_legs_qs.exists():
            validation_error = ', '.join([x.__str__() for x in is_conflict_with_next_legs_qs])
            raise ValidationError(validation_error_text + validation_error)

    # Apply changes to the current flight leg
    mission_leg.updated_by = updated_by
    if commit:
        mission_leg.save()

    # Apply changes to the subsequent flight legs (if requested)
    if roll_change_to_subsequent_legs:
        legs_to_delay = mission_leg.mission.active_legs.filter(sequence_id__gt=mission_leg.sequence_id)
        for leg_to_delay in legs_to_delay:
            leg_to_delay.departure_datetime = leg_to_delay.departure_datetime + delta
            leg_to_delay.arrival_datetime = leg_to_delay.arrival_datetime + delta
            leg_to_delay.updated_by = updated_by
            if commit:
                leg_to_delay.save()

    return mission_leg


def mission_legs_update_consistency(mission):
    # Function to update mission legs after it's changing
    legs_to_update = []

    # Unset 'previous_leg' for all flight legs
    for mission_leg in mission.active_legs:
        mission_leg.meta_is_maintenance_save = True
        mission_leg.previous_leg = None
        mission_leg.save()

    for leg in mission.active_legs:
        prev_leg = mission.active_legs.filter(sequence_id=leg.sequence_id - 1).first()
        leg.previous_leg = prev_leg
        legs_to_update.append(leg)

    for leg in legs_to_update:
        leg.meta_is_maintenance_save = True
        leg.prevent_mission_update = True
        leg.save()

    return


def mission_legs_enumerate(mission):
    # Function to re-calculate Mission Legs sequence if after deleting any of them
    active_legs = mission.active_legs

    for index, leg in enumerate(active_legs, 1):
        leg.sequence_id = index
        leg.prevent_mission_update = True
        leg.save()

    return
