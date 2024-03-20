import logging

from django.db.models import Q
from django.db.models.signals import post_save

from handling.models import HandlingRequestMovement, HandlingRequest, HandlingRequestServices
from handling.utils.email_diff_generator import generate_diff_dict
from handling.utils.handling_request_func import handling_request_cancel_actions
from mission.models import MissionTurnaround, MissionLegCargoPayload, MissionLegPassengersPayload

logger = logging.getLogger(__name__)


def mission_sfr_movement_update_services(movement, turnaround):
    if movement.direction_code == 'arrival':
        q = Q(on_arrival=True)
    else:
        q = Q(on_departure=True)

    for requested_service in turnaround.requested_services.filter(q).all():

        defaults = {
            'note': requested_service.note,
            'booking_text': requested_service.booking_text,
            'booking_quantity': requested_service.booking_quantity,
            'booking_quantity_uom': requested_service.booking_quantity_uom,
        }

        try:
            obj = HandlingRequestServices.objects.get(movement=movement, service=requested_service.service)
            for key, value in defaults.items():
                setattr(obj, key, value)
                if movement.request.created:
                    setattr(obj, 'supress_amendment', True)
        except HandlingRequestServices.DoesNotExist:
            obj = HandlingRequestServices(**defaults)
            obj.movement = movement
            obj.service = requested_service.service

        obj.updated_by = movement.updated_by
        obj.sfr_service_meta_prevent_sfr_save = True
        obj.save()


def create_or_update_mission_sfr(turnaround, author):
    mission = turnaround.mission_leg.mission
    flight_leg_left = turnaround.mission_leg
    flight_leg_right = turnaround.mission_leg.get_next_leg()

    # Create or Update S&F Request
    handling_request = turnaround.handling_request or HandlingRequest(
        created_by=mission.created_by, is_standalone=False)

    handling_request.created = not handling_request.pk

    # Compare the old and new turnaround location. If different, cancel the old request, and create
    # a new one from scratch (per Adrian, nothing is transferable between old and new request in such case) - LP
    if not handling_request.created and handling_request.airport != turnaround.mission_leg.arrival_location:
        handling_request_cancel_actions(handling_request=handling_request, author=author)
        logger.info(f'Mission > SFR Bridge: Mission #{mission.pk}: S&F Request #{handling_request.pk} Cancelled'
                    f' (to be recreated)')
        handling_request = HandlingRequest(created_by=author, is_standalone=False)
        handling_request.created = True

    # Create diff dict for amendment notifications
    old_instance_diff = None
    if not handling_request.created:
        old_instance_diff = generate_diff_dict(handling_request=handling_request)

    handling_request.customer_organisation = mission.organisation
    handling_request.airport = turnaround.mission_leg.arrival_location
    handling_request.callsign = turnaround.mission_leg.callsign_override or mission.callsign
    handling_request.mission_number = turnaround.mission_leg.mission.mission_number_repr
    handling_request.aircraft_type = turnaround.mission_leg.aircraft_type_override or mission.aircraft_type
    handling_request.apacs_number = mission.apacs_number
    handling_request.apacs_url = mission.apacs_url
    handling_request.tail_number = turnaround.mission_leg.aircraft_override or mission.aircraft

    # S&F Request Fuel
    handling_request.fuel_required = turnaround.fuel_required
    handling_request.fuel_quantity = turnaround.fuel_quantity
    handling_request.fuel_unit = turnaround.fuel_unit
    handling_request.fuel_prist_required = turnaround.fuel_prist_required

    handling_request.updated_by = author

    # First save in case of
    if handling_request.created:
        handling_request.skip_signal = True
        handling_request.save()
        delattr(handling_request, 'skip_signal')

    # Copy Mission Crew to S&F Request Crew
    for mission_crew_position in turnaround.mission_leg.crew_positions.all():
        handling_request.mission_crew.update_or_create(
            person=mission_crew_position.person,
            defaults={
                'position': mission_crew_position.position,
                'is_primary_contact': mission_crew_position.is_primary_contact,
                'can_update_mission': mission_crew_position.can_update_mission,
            }
        )

    # Create or Update Arrival Movement
    arrival_movement = handling_request.arrival_movement or HandlingRequestMovement(direction_id='ARRIVAL')
    arrival_movement.request = handling_request
    arrival_movement.date = flight_leg_left.arrival_datetime
    arrival_movement.airport = flight_leg_left.departure_location
    arrival_movement.crew = flight_leg_left.pob_crew
    arrival_movement.is_passengers_onboard = False if flight_leg_left.pob_pax is None else True
    arrival_movement.is_passengers_tbc = True if flight_leg_left.pob_pax == 0 else False
    arrival_movement.passengers = flight_leg_left.pob_pax

    arrival_movement.updated_by = author
    arrival_movement.movement_meta_prevent_sfr_save = True
    arrival_movement.save()

    if arrival_movement.amendment_fields.intersection(arrival_movement.changed_fields):
        handling_request.is_movement_amended = True

    # Create or Update Departure Movement
    departure_movement = handling_request.departure_movement or HandlingRequestMovement(direction_id='DEPARTURE')
    departure_movement.request = handling_request
    departure_movement.date = flight_leg_right.departure_datetime
    departure_movement.airport = flight_leg_right.arrival_location
    departure_movement.crew = flight_leg_right.pob_crew
    departure_movement.is_passengers_onboard = False if flight_leg_right.pob_pax is None else True
    departure_movement.is_passengers_tbc = True if flight_leg_right.pob_pax == 0 else False
    departure_movement.passengers = flight_leg_right.pob_pax

    departure_movement.updated_by = author
    departure_movement.movement_meta_prevent_sfr_save = True
    departure_movement.save()

    if departure_movement.amendment_fields.intersection(departure_movement.changed_fields):
        handling_request.is_movement_amended = True

    mission_sfr_movement_update_services(arrival_movement, turnaround)
    mission_sfr_movement_update_services(departure_movement, turnaround)

    handling_request.supress_amendment_notifications = False
    handling_request.old_instance_diff = old_instance_diff
    handling_request.save()
    if handling_request.created:
        # Trigger post_save signal to create/update fuel order
        post_save.send(HandlingRequest, instance=handling_request, created=handling_request.created)

    turnaround.handling_request = handling_request

    # Update S&F Request Payload data
    for passenger in turnaround.mission_leg.passengers.all():
        post_save.send(MissionLegPassengersPayload, instance=passenger, created=handling_request.created)
    for cargo in turnaround.mission_leg.cargo.all():
        post_save.send(MissionLegCargoPayload, instance=cargo, created=handling_request.created)

    return handling_request


def mission_sfr_bridge(mission, author):
    logger.info('Mission > SFR Bridge: Started')
    turnarounds = MissionTurnaround.objects.using('default').filter(mission_leg__mission=mission)
    logger.info(f'Mission > SFR Bridge: Turnarounds to Update: {turnarounds}')

    for turnaround in turnarounds:
        if turnaround.mission_leg.arrival_aml_service and not turnaround.mission_leg.is_cancelled and \
                not mission.is_cancelled:
            handling_request = create_or_update_mission_sfr(turnaround, author=author)
            if handling_request.created:
                logger.info(f'Mission > SFR Bridge: Mission #{mission.pk}: S&F Request #{handling_request.pk} Created')
            else:
                logger.info(f'Mission > SFR Bridge: Mission #{mission.pk}: S&F Request #{handling_request.pk} Updated')
            logger.info(f'Mission > SFR Bridge: S&F Request {handling_request.pk} will be added '
                        f'to the Turnaround {turnaround.pk}')
            MissionTurnaround.objects.filter(pk=turnaround.pk).update(handling_request_id=handling_request.pk)

        elif turnaround.handling_request:
            if turnaround.handling_request.mission_turnaround.mission_leg.mission.is_cancelled:
                reason = 'mission cancellation'
            elif turnaround.handling_request.mission_turnaround.mission_leg.is_cancelled:
                reason = 'mission leg cancellation'
            else:
                reason = 'mission itinerary change'
            logger.info(f'Mission > SFR Bridge: Cancel S&F Request for Flight Leg {turnaround.mission_leg}')
            handling_request_cancel_actions(handling_request=turnaround.handling_request, author=author,
                                            auto_cancellation_reason=reason)

            if not turnaround.mission_leg.arrival_aml_service:
                turnaround.handling_request = None
                turnaround.save()
