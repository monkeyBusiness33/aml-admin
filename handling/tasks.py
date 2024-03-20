import json

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.urls import reverse

from handling.models import HandlingRequest, HandlingRequestServices, ServiceProvisionForm, HandlingRequestDocument
from handling.models.handling_request_documents import signable_invoice_chase_notification_task  # Celery requirement
from handling.utils.client_notifications import handling_request_push_notification, spf_received_push_notification
from handling.utils.document_signing import invoice_signing_email_notification, invoice_signing_push_notification
from handling.utils.email_diff_generator import HandlingRequestDiff
from handling.utils.handling_request_urls import get_firebase_dynamic_link
from handling.utils.staff_notifications import spf_submission_staff_notifications
from handling.utils.spf import create_spf_document
from core.tasks import send_email, send_whatsapp_message
from django.template.loader import render_to_string

logger = get_task_logger(__name__)


@shared_task
def handling_request_notify_dao(handling_request_id):
    """
    This function send "Notify DAO" email message to the destination country DAO if it requested in the handling request
    :param handling_request_id: HandlingRequest PK
    :return: None
    """
    handling_request = HandlingRequest.objects.get(pk=handling_request_id)
    requested_services = HandlingRequestServices.objects.filter(movement__request=handling_request).all()
    dao_emails = handling_request.airport.airport_details.region.country.country_dao.all().values_list(
        'organisation__dao_details__contact_email_1',
        'organisation__dao_details__contact_email_2',
    )
    import itertools
    dao_email_list = list(itertools.chain(*dao_emails))

    primary_contact = getattr(handling_request, 'primary_contact')
    person_repr = None

    if primary_contact:
        person_details = getattr(primary_contact, 'details')
        person_repr = f'{person_details.first_name} {person_details.last_name}'
        person_repr += f', {handling_request.customer_organisation.details.registered_name}'
        if person_details.contact_phone:
            person_repr += f', {person_details.contact_phone}'
        if person_details.contact_email:
            person_repr += f', {person_details.contact_email}'

    if dao_email_list:

        subject = 'US Military Flight Notification - {callsign} / {airport} / {arrival_datetime}Z'.format(
            callsign=handling_request.callsign,
            airport=handling_request.location_tiny_repr,
            arrival_datetime=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
        )
        body = render_to_string(
            'email/notify_dao.html',
            {
                'handling_request': handling_request,
                'requested_services': requested_services,
                'person_repr': person_repr,
            })

        send_email(
            subject=subject,
            body=body,
            recipient=dao_email_list,
        )


@shared_task
def send_missed_push_notifications():
    handling_requests = HandlingRequest.objects.with_status().filter(
        is_booking_notifications_sent__isnull=True,
        cancelled=False,
        fuel_booking__isnull=False
    ).all()

    for handling_request in handling_requests:
        if handling_request.status not in [4, 7]:
            handling_request_push_notification(handling_request.pk)


@shared_task
def spf_submission_post_processing(spf_id):
    """
    Function to executed needed actions after the SPF submitted or amended
    :param spf_id: ServiceProvisionForm PK
    :return: None
    """
    spf = ServiceProvisionForm.objects.get(pk=spf_id)

    # Send push notifications
    spf_received_push_notification(spf_id)
    spf_submission_staff_notifications(spf_id)

    # Send SPF PDF via email
    spf_document = create_spf_document(spf)

    subject = 'Service Provision Form Received - {callsign} / {icao_iata}'.format(
        callsign=spf.handling_request.callsign,
        icao_iata=spf.handling_request.location_short_repr,
    )

    body = render_to_string(
        'email/spf_document.html',
        {'handling_request': spf.handling_request}
    )

    send_email(
        subject=subject,
        body=body,
        recipient=spf.handling_request.primary_contact.details.contact_email,
        cc=settings.EMAIL_AML_SPF,
        attachments=[spf_document],
    )


@shared_task
def handling_request_send_fuel_team_booking_invite(handling_request_id, amendment: bool = False, amended_fields=None):
    """
    This function send "DoD Fuel Order" email to the fuel team
    :param handling_request_id: HandlingRequest PK
    :param amended_fields: List of dicts of amended data
    :param amendment: boolean
    :return:
    """
    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()

    # Stop execution if S&F Request have no fuel requested
    if not handling_request.fuel_required:
        return None

    state = 'UPDATE' if amendment else 'NEW'
    urgent_state_text = '**URGENT** ' if handling_request.is_urgent else ''

    subject = '{urgent}{state} - DoD Fuel Order - {callsign} / {airport} / {arrival_datetime}Z'.format(
        urgent=urgent_state_text,
        state=state,
        callsign=handling_request.callsign,
        airport=handling_request.location_tiny_repr,
        arrival_datetime=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
    )
    if amendment:
        handling_request_diff_json = json.loads(amended_fields)
        diff_obj = HandlingRequestDiff(handling_request_diff_json)

        body = render_to_string(
            'email/dod_fuel_order_update.html',
            {
                'handling_request': handling_request,
                'amendment': amendment,
                'diff_obj': diff_obj,
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
                'fuel_booking_confirmation_url': reverse('admin:fuel_booking_confirmation',
                                                         kwargs={'pk': handling_request.pk}),
            })
    else:
        body = render_to_string(
            'email/dod_fuel_order.html',
            {
                'handling_request': handling_request,
                'amendment': amendment,
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
                'fuel_booking_confirmation_url': reverse('admin:fuel_booking_confirmation',
                                                         kwargs={'pk': handling_request.pk}),
            })

    send_email(
        subject=subject,
        body=body,
        recipient=['fuelteam@amlglobal.net'],
    )


@shared_task
def handling_request_submitted_staff_notification(handling_request_id):
    """
    This function send "New Servicing & Fueling Request" email to the "Military Team"
    :param handling_request_id: HandlingRequest PK
    :return:
    """
    from user.models import Person

    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()

    if handling_request.is_new and not handling_request.created_by.user.is_staff:

        subject = 'New Servicing & Fueling Request - {callsign} / {airport} / {arrival_datetime}Z'.format(
            callsign=handling_request.callsign,
            airport=handling_request.location_tiny_repr,
            arrival_datetime=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M")
        )
        body = render_to_string(
            'email/handling_request_new.html',
            {
                'handling_request': handling_request,
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
                'handling_request_url': reverse('admin:handling_request', kwargs={'pk': handling_request.pk}),
            })

        send_email(
            subject=subject,
            body=body,
            recipient=['ops@amlglobal.net'],
        )

    # Send URGENT WhatsApp notification
    if handling_request.is_new and handling_request.is_urgent and not handling_request.created_by.user.is_staff:

        handling_request_url = get_firebase_dynamic_link(handling_request)

        body = 'A new urgent servicing & fueling request received: \n\n' \
               'ETA: {eta} \n' \
               'Callsign: {callsign} \n' \
               'Location: {location} \n\n' \
               'Please access the servicing & fueling request in the ' \
               'Operations Portal, or via the mobile app Admin section: {handling_request_url} \n' \
               'This is an automated message, please do not reply'.format(

                eta=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
                callsign=handling_request.callsign,
                location=handling_request.location_tiny_repr,
                handling_request_url=handling_request_url,
                )

        military_team_phones = Person.objects.filter(
            user__roles=1000).values_list('details__contact_phone', flat=True)
        if military_team_phones:
            send_whatsapp_message(body, military_team_phones)


@shared_task
def handler_parking_confirmation_notification():
    from handling.utils.handler_notifications import handler_parking_confirmation_email
    handler_parking_confirmation_email()


@shared_task
def invoice_signing_notifications(document_id):
    document = HandlingRequestDocument.objects.filter(pk=document_id).first()
    invoice_signing_email_notification(document)
    invoice_signing_push_notification(document)


@shared_task
def handling_request_invalidate_cache_task(handling_request_id):
    handling_request = HandlingRequest.objects.detailed_list().filter(pk=handling_request_id).first()
    handling_request.invalidate_cache()
