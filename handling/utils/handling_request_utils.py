import json
import logging

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from handling.utils.staff_notifications import staff_aog_notifications
from organisation.models import HandlerCancellationBandTerm

logger = logging.getLogger(__name__)


def handling_request_ground_handling_cancellation(handling_request):
    from handling.utils.spf_auto import send_ground_handling_spf_cancellation_email

    handling_request.is_handling_confirmed = False
    # Process only if Ground Handling already has been sent
    if hasattr(handling_request, 'auto_spf') and handling_request.auto_spf.sent_to:
        # Send cancellation email if handling_agent changed or 'cancel_ground_handling' attr supplied
        if handling_request.handling_agent != handling_request.auto_spf.sent_to or hasattr(handling_request,
                                                                                           'cancel_ground_handling'):
            # Send email if it is not suppressed
            if not handling_request.supress_gh_cancellation_email:
                send_ground_handling_spf_cancellation_email(handling_request_id=handling_request.pk,
                                                            requester_person_id=handling_request.updated_by.pk)

        handling_request.auto_spf.delete()
        handling_request.amendment_sessions.update(is_gh_opened=False)

        handling_request.activity_log.create(
            author=handling_request.updated_by,
            record_slug='sfr_ground_handling_confirmation_cancellation',
            details=f'Ground Handling for "{handling_request.auto_spf.sent_to.full_repr}" has been cancelled',
        )

    return handling_request


def handling_request_ground_handling_confirmation(handling_request):
    from handling.models import HandlingRequestServices

    if hasattr(handling_request, 'confirm_handling_services'):
        HandlingRequestServices.objects.filter(
            movement__request=handling_request
        ).update(booking_confirmed=True)

    return handling_request


def handling_request_on_save(handling_request):
    """
    Function executes on each S&F Request saving, updates required details when needed
    :param handling_request: S&F Request instance
    :return:
    """
    from handling.models import HandlingRequestFuelBooking, HandlingRequestServices

    # Clear Fuel details when fuel unrequested
    if 'fuel_required_id' in handling_request.changed_fields and not handling_request.fuel_required:
        handling_request.fuel_quantity = None
        handling_request.fuel_unit = None
        handling_request.fuel_prist_required = False

    # Mark S&F Request as callsign amended
    if 'callsign' in handling_request.changed_fields:
        handling_request.is_amended_callsign = True

        # Reset related Fuel Order completely on callsign change
        HandlingRequestFuelBooking.objects.filter(handling_request=handling_request).delete()

    # Reset S&F Request services booking state on tail number amendment
    if 'tail_number_id' in handling_request.changed_fields:
        HandlingRequestServices.objects.filter(
            movement__request=handling_request).update(booking_confirmed=None)

    if not hasattr(handling_request, 'updated_by') or handling_request.updated_by is None:
        if settings.DEBUG:
            logger.error('S&F Request have no "updated_by" attribute')
        return

    modified_by_staff = handling_request.updated_by.user.is_staff

    if not modified_by_staff:
        if not handling_request.is_new:
            # Set "AMENDED" status on change of specific fields
            if handling_request.amendment_fields.intersection(handling_request.changed_fields) \
                    or handling_request.is_movement_amended or handling_request.is_services_amended:
                handling_request.amended = True

    if modified_by_staff:
        # Remove "New" state on any update
        handling_request.is_new = False

        if not hasattr(handling_request, 'force_amendment'):
            handling_request.amended = False

        if not handling_request.assigned_mil_team_member:
            if handling_request.updated_by and handling_request.updated_by.is_mil_team:
                handling_request.assigned_mil_team_member = handling_request.updated_by

        if 'callsign' not in handling_request.changed_fields:
            handling_request.is_amended_callsign = False

        # In case of 'handling_agent' change or 'cancel_ground_handling' process Ground Handling Cancellation
        if 'handling_agent_id' in handling_request.changed_fields or hasattr(handling_request,
                                                                             'cancel_ground_handling'):
            handling_request = handling_request_ground_handling_cancellation(handling_request)

        handling_confirmation_fields = ['is_handling_confirmed', 'is_awaiting_departure_update_confirmation']

        if set(handling_confirmation_fields).intersection(handling_request.changed_fields):
            handling_request = handling_request_ground_handling_confirmation(handling_request)

    # Final amendment rules for all
    amendment_fields = {'fuel_required_id', 'fuel_quantity', 'fuel_unit_id', 'aircraft_type_id'}

    if amendment_fields.intersection(handling_request.changed_fields):
        handling_request.amended = True

    if handling_request.fuel_amendment_fields.intersection(handling_request.changed_fields):
        if hasattr(handling_request, 'mission_turnaround'):
            handling_request.mission_turnaround.fuel_required_id = handling_request.fuel_required_id
            handling_request.mission_turnaround.fuel_quantity = handling_request.fuel_quantity
            handling_request.mission_turnaround.fuel_unit_id = handling_request.fuel_unit_id
            handling_request.mission_turnaround.fuel_prist_required = handling_request.fuel_prist_required
            handling_request.mission_turnaround.save()

    return handling_request


def handling_request_amendment_notifications(handling_request, old_instance_diff):
    from handling.utils.email_diff_generator import generate_diff_dict, json_serializer
    from handling.utils.staff_notifications import staff_amendment_notifications
    from handling.tasks import handling_request_send_fuel_team_booking_invite
    from handling.utils.client_notifications import handling_request_push_notification
    from handling.utils.fuel_booking_notifications import staff_fuel_booking_cancelled_notification

    logger.info(f'S&F Request #{handling_request.pk}: Amendment notifications being sent')

    if not hasattr(handling_request, 'updated_by') or handling_request.updated_by is None:
        logger.warning('S&F Request have no "updated_by" attribute')
        return

    modified_by_staff = handling_request.updated_by.user.is_staff

    # Send user push notification
    handling_request_push_notification.delay(handling_request.pk)

    # Update S&F Request Amendment diff and serialize
    handling_request_diff = generate_diff_dict(handling_request, existing_amendment_data=old_instance_diff)
    handling_request_diff_json = json.dumps(handling_request_diff, default=json_serializer)

    """
    Fuel Booking Amendment
    """
    # Process Fuel cancellation
    if 'fuel_required_id' in handling_request.changed_fields and not handling_request.fuel_required:
        staff_fuel_booking_cancelled_notification.apply_async(
            kwargs={'handling_request': handling_request.pk, 'amendment': True}, countdown=3)

    # Process fuel amendment
    elif handling_request.amendment_fields.intersection(handling_request.changed_fields) \
            or handling_request.is_fuel_related_data_amended:
        handling_request_send_fuel_team_booking_invite.apply_async(
            kwargs={'handling_request_id': handling_request.pk, 'amendment': True,
                    'amended_fields': handling_request_diff_json, }, countdown=3)

    """
    S&F Request amendment
    """
    # Supress amendment notification in case if S&F Request modified by staff
    if modified_by_staff and not settings.DEBUG:
        return

    if 'is_aog' in handling_request.changed_fields and handling_request.is_aog:
        staff_aog_notifications(handling_request=handling_request, author=handling_request.updated_by)

    if handling_request.amendment_fields.intersection(handling_request.changed_fields) \
            or handling_request.is_movement_amended or handling_request.is_services_amended:
        staff_amendment_notifications.delay(handling_request=handling_request.pk,
                                            amended_fields=handling_request_diff_json,
                                            author=handling_request.updated_by.pk)


def sfr_get_cancellation_terms(handling_request):
    if not handling_request.handling_agent:
        return None

    diff = handling_request.get_eta_date() - timezone.now()
    hours_until_eta = divmod(diff.total_seconds(), 3600)[0]

    if hours_until_eta < 0:
        return None

    applicable_bands_qs = handling_request.handling_agent.handler_cancellation_bands.filter(
        (Q(notification_band_start_hours__lte=hours_until_eta) & Q(notification_band_end_hours__gte=hours_until_eta))
        |
        (Q(notification_band_start_hours__lte=hours_until_eta) & Q(notification_band_end_hours__isnull=True))
    )
    applicable_terms = HandlerCancellationBandTerm.objects.filter(cancellation_band__in=applicable_bands_qs)
    return applicable_terms
