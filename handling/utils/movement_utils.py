import logging

logger = logging.getLogger(__name__)


def movement_add_mandatory_services(movement):
    from handling.models import HandlingService

    """
    Passengers Handling service
    """
    passengers_handling_service = HandlingService.objects.filter(
        is_active=True,
        codename='passengers_handling',
    ).first()

    if movement.is_passengers_onboard and passengers_handling_service:
        movement.hr_services.update_or_create(service=passengers_handling_service)

    """
    Generic "Always Included" services
    """
    always_included_services = HandlingService.objects.filter(
        is_active=True,
        always_included=True
    )

    for service in always_included_services:
        movement.hr_services.update_or_create(service=service)


def movement_amendment(movement, handling_request_diff):

    if hasattr(movement, 'supress_amendment'):
        logger.warning(f'Movement {movement.pk}: Amendment suppressed')
        return

    movement.request.old_instance_diff = handling_request_diff

    from handling.models import HandlingRequestFuelBooking, HandlingRequestServices
    if 'date' in movement.changed_fields and not movement.movement_meta_retain_fuel_order:
        movement.request.is_fuel_related_data_amended = True

    # Amend S&F Request and send amendment notifications
    if movement.amendment_fields.intersection(movement.changed_fields) and \
        not movement.movement_meta_retain_gh_confirmation:
        movement.is_amended = True
        movement.request.is_movement_amended = True

        # Process amendment in grace period
        is_departure_editing_grace_period = getattr(movement.request, 'is_departure_editing_grace_period', None)
        if movement.direction_id == 'DEPARTURE' and is_departure_editing_grace_period:
            # Do not amend movement in case when S&F Request is not amended
            if not movement.request.amended:
                movement.request.is_movement_amended = False
        else:
            if movement.request.fuel_required and movement.request.is_fuel_related_data_amended:
                HandlingRequestFuelBooking.objects.filter(handling_request=movement.request).delete()

            # if movement.amendment_fields.intersection(movement.changed_fields):
            HandlingRequestServices.objects.filter(movement__request=movement.request).update(booking_confirmed=None)

            movement.request.is_handling_confirmed = False
            movement.request.parking_apron = None
            movement.request.parking_stand = None
            movement.request.force_amendment = True  # Do not reset "AMENDED" S&F Request status
            movement.request.reset_handler_parking_confirmation_state()

        if movement.request.changed_fields and 'is_aog' in movement.request.changed_fields:
            is_aog_field_diff = movement.request.get_field_diff('is_aog')
            if is_aog_field_diff[0] is True and is_aog_field_diff[1] is False:
                movement.request.is_movement_amended = False
                movement.request.amended = False
            else:
                movement.request.is_movement_amended = True

    movement.request.updated_by = movement.updated_by
    if not movement.movement_meta_prevent_sfr_save:
        movement.request.save()
