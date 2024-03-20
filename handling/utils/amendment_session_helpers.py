

def create_amendment_session_record(handling_request):
    # Fetch original instance
    from handling.models import HandlingRequest
    handling_request_orig = HandlingRequest.objects.get(pk=handling_request.pk)

    if not hasattr(handling_request_orig, 'auto_spf'):
        return True

    amendment_session, created = handling_request.amendment_sessions.filter(
        is_gh_opened=True,
    ).get_or_create(
        handling_request=handling_request,
    )
    if not created:
        return amendment_session

    # For a newly created amendment session for departure update after arrival, set the relevant flag
    if getattr(handling_request, 'set_is_departure_update_after_arrival', False):
        amendment_session.is_departure_update_after_arrival = True

    for field_name in ['callsign', 'tail_number_id', 'aircraft_type_id', ]:
        setattr(amendment_session, field_name, getattr(handling_request_orig, field_name))

    for field_name in ['date', 'airport_id', 'is_passengers_onboard', 'is_passengers_tbc', 'passengers', ]:
        setattr(amendment_session,
                f'{handling_request_orig.arrival_movement.direction_code}_{field_name}',
                getattr(handling_request.arrival_movement, field_name),
                )

        setattr(amendment_session,
                f'{handling_request_orig.departure_movement.direction_code}_{field_name}',
                getattr(handling_request.departure_movement, field_name),
                )

    amendment_session.save()
    return amendment_session


def update_amendment_session_services(handling_request, direction_code, hr_service, is_added=False, is_removed=False):
    """
    This function creates initial list of services for S&F Request in the handling_requests_amendment_sessions_services
    And then mark newly added or existing services as added/removed
    Newly added services will be removed instead marking as removed
    Initial services will be removed if it removed from S&F Request
    Added services will be removed if it removed from S&F Request
    :param handling_request: HandlingRequest instance
    :param direction_code: Movement direction code such as "ARRIVAL"
    :param hr_service: HandlingService instance
    :param is_added: Is service has added in current amendment session
    :param is_removed: Is initial service has been removed during current amendment session
    :return:
    """
    if not hasattr(handling_request, 'auto_spf'):
        return True

    amendment_session = create_amendment_session_record(handling_request)

    # If we are adding departure services after arrival has occurred, we don't reset the handling status
    if not amendment_session.is_departure_update_after_arrival:
        handling_request.is_handling_confirmed = False

    # Fill services that was initially in the S&F Request
    if not amendment_session.session_services.filter(direction_id=direction_code).exists():
        existing_services = hr_service.movement.hr_services.values(
            'service_id', 'booking_quantity', 'booking_quantity_uom_id', 'booking_text')

        for existing_service in existing_services:
            amendment_session.session_services.create(
                service_id=existing_service['service_id'],
                direction_id=direction_code,
                booking_quantity=existing_service['booking_quantity'],
                booking_quantity_uom_id=existing_service['booking_quantity_uom_id'],
                booking_text=existing_service['booking_text']
            )

    # Append added service
    if is_added:
        # Update existing service
        if amendment_session.session_services.filter(service=hr_service.service, is_added=False).exists():
            amendment_session.session_services.filter(service=hr_service.service, is_added=False).update(
                booking_quantity=hr_service.booking_quantity,
                booking_quantity_uom=hr_service.booking_quantity_uom,
                booking_text=hr_service.booking_text,
                is_removed=False)
        else:
            amendment_session.session_services.update_or_create(
                service=hr_service.service,
                defaults={
                    'is_added': is_added,
                    'direction_id': direction_code,
                    'booking_quantity': hr_service.booking_quantity,
                    'booking_quantity_uom': hr_service.booking_quantity_uom,
                    'booking_text': hr_service.booking_text,
                }
            )

    if is_removed:
        # Remove service that was added in current amendment session
        amendment_session.session_services.filter(service=hr_service.service, is_added=True).delete()
        # Mark as removed service that was present before session started
        amendment_session.session_services.filter(service=hr_service.service, is_added=False).update(
            booking_quantity=hr_service.booking_quantity,
            booking_quantity_uom=hr_service.booking_quantity_uom,
            booking_text=hr_service.booking_text,
            is_removed=True)
