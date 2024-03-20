from core.tasks import send_push
from celery import shared_task
from handling.models import HandlingRequest, ServiceProvisionForm
from user.models import Person


@shared_task
def handling_request_push_notification(handling_request_id, force_notification=False):
    """
    Function to generate Handling Request user push notification message text and data
    :param handling_request_id: Handling Request PK
    :param force_notification: boolean to ignore duplicate prevention
    :return:
    """
    # Load Handling Request instance with included status data
    handling_request = HandlingRequest.objects.with_status().filter(pk=handling_request_id).first()
    if not handling_request.is_booking_notifications_sent or force_notification is True:

        # Get Handling Request arrival movement
        arrival_movement = handling_request.movement.filter(direction_id='ARRIVAL').first()
        body = None
        users_to_notify = getattr(handling_request, 'crew_users', None)

        if handling_request.booking_completed and not handling_request.cancelled:
            # Generate notification body
            if handling_request.status in [2, 8]:
                # Handling Request fully confirmed
                body = 'Fueling and servicing is now fully confirmed for this turnaround.'
            elif handling_request.status == 3:
                if handling_request.services_booking_confirmed == 0 and hasattr(handling_request, 'fuel_booking'):
                    body = 'All requested services are not available. Please contact the AML operations team for ' \
                           'assistance. '
                else:
                    # Handling Request partially confirmed
                    body = 'One or more requested services are not available. Please contact the AML operations team ' \
                           'for assistance. '

            if body and users_to_notify:
                send_push(
                    '{callsign} / {location} / {arrival_date}'.format(
                        callsign=handling_request.callsign,
                        location=handling_request.location_tiny_repr,
                        arrival_date=arrival_movement.date.strftime("%b-%d-%Y"),
                    ),
                    body,
                    {'handling_request_id': str(handling_request.id)},
                    list(users_to_notify)
                )
                handling_request.is_booking_notifications_sent = True
                handling_request.save()


@shared_task
def handling_request_updated_services_push_notification(handling_request):
    """
    Function to generate silent push notification to client user on handling request update
    :param handling_request: S&F Request instance
    :return:
    """
    users_to_notify = handling_request.crew_users.values_list('pk', flat=True)

    if handling_request.booking_completed and users_to_notify:
        send_push.delay(
            data={
                'handling_request_id': str(handling_request.id),
                'notification_type': 'handling_request_update',
                'handling_request_header': '{callsign} / {location} / {arrival_date}'.format(
                    callsign=handling_request.callsign,
                    location=handling_request.location_tiny_repr,
                    arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
                ),
                'handling_request_update_text': 'Handling request has been updated by staff, please check it.',
            },
            users=list(users_to_notify)
        )


@shared_task
def handling_request_received_push_notification(handling_request):
    """
    Function to generate push notification to client user on handling request receive
    :param handling_request: HandlingRequest PK
    :return:
    """
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.get(pk=handling_request)

    users_to_notify = getattr(handling_request, 'crew_users', None)

    if users_to_notify:
        send_push(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
                arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='The servicing and fuelling request for flight {callsign} at {location} has been received by the AML '
                 'team and is being processed.'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
            ),
            data={
                'handling_request_id': str(handling_request.id),
            },
            users=list(users_to_notify)
        )


@shared_task
def handling_request_added_to_crew_push_notification(handling_request_id: int, person_id: int):
    """
    Function to generate push notification to client user when he added to crew
    :param person_id: Person PK
    :param handling_request_id: HandlingRequest PK
    :return:
    """
    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()
    person = Person.objects.filter(pk=person_id).first()
    user_to_notify = getattr(person, 'user', None)

    if user_to_notify:
        send_push(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
                arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='You have been assigned as crew for {callsign} on {arrival_date}'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
                arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            data={
                'handling_request_id': str(handling_request.id),
            },
            users=[user_to_notify],
        )


@shared_task
def handling_request_unable_to_support_notification(handling_request_id: int):
    """
    Function to generate "Unable to Support" push notification to S&F Request crew
    :param handling_request_id: HandlingRequest PK
    :return:
    """
    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()
    users_to_notify = getattr(handling_request, 'crew_users', None)

    if users_to_notify and handling_request.is_unable_to_support:
        send_push(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
                arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='AML are unable to provide support. Please see the servicing & fueling request screen for more '
                 'details'.format(
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
            ),
            data={
                'handling_request_id': str(handling_request.id),
            },
            users=list(users_to_notify)
        )


@shared_task
def spf_received_push_notification(spf_id):
    """
    Function to generate push notification to client user on SPF receive
    :param spf_id: ServiceProvisionForm PK
    :return:
    """
    spf = ServiceProvisionForm.objects.get(pk=spf_id)
    users_to_notify = getattr(spf.handling_request, 'crew_manager_users', None)

    if users_to_notify:
        send_push(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=spf.handling_request.callsign,
                location=spf.handling_request.location_tiny_repr,
                arrival_date=spf.handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='Service Provision Form for flight {callsign} at {location} has been received by the AML team and is '
                 'being processed.'.format(
                callsign=spf.handling_request.callsign,
                location=spf.handling_request.location_tiny_repr,
            ),
            data={
                'spf_id': str(spf.id),
            },
            users=list(users_to_notify)
        )
