from datetime import timedelta

from django.conf import settings
from django.db.models import Min, Max, ExpressionWrapper, DateTimeField, F
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone

from core.tasks import send_email
from handling.models import HandlingRequest
from organisation.models import EmailFunction


def handler_parking_confirmation_email():
    """
    Send email message to the Handler (handling_agent) for S&F Request which have no confirmed parking
    :return:
    """
    handling_requests = HandlingRequest.objects.with_status().annotate(
        arrival_date=Min('movement__date'),
        departure_date=Max('movement__date'),
        arrival_12h_before_date=ExpressionWrapper(
            F('arrival_date') - timedelta(hours=12),
            output_field=DateTimeField()
        ),
    ).filter(
        status__in=[1, 2, 8, ],
        parking_apron__isnull=True,
        parking_confirmed_on_day_of_arrival=False,
        notifications__is_handler_parking_confirmation_email_sent=False,
        airport__details__type_id=8,
        handling_agent__isnull=False,
        is_handling_confirmed=True,
        arrival_date__gte=timezone.now(),
        arrival_12h_before_date__lte=timezone.now(),
        departure_date__gt=timezone.now(),
    )

    for handling_request in handling_requests:
        # Get options for Parking Case Email
        ground_handler = handling_request.handling_agent
        ground_handler_ops_details = getattr(ground_handler, 'ops_details')

        # Send email message in case if it enabled for Ground Handler
        if ground_handler_ops_details.receives_parking_chase_email:

            # Addresses TO
            addresses_to = handling_request.handling_agent.get_email_address()

            # Addresses CC and BCC
            email_function, created = EmailFunction.objects.get_or_create(
                codename='ground_handler_parking_confirmation')
            addresses_cc = email_function.get_addresses_cc(handling_request.handling_agent)
            addresses_cc.append('ops@amlglobal.net')
            addresses_bcc = email_function.get_addresses_bcc(handling_request.handling_agent)

            subject = 'Request for Confirmation of Parking Apron & Stand for {callsign} ({aircraft_designator}) - ' \
                      '{location} - {arrival_date} / {departure_date}'.format(
                        callsign=handling_request.callsign,
                        aircraft_designator=handling_request.aircraft_type.designator,
                        location=handling_request.location_short_repr,
                        arrival_date=handling_request.arrival_movement.date_capitalized,
                        departure_date=handling_request.departure_movement.date_capitalized,
                        )

            body = render_to_string(
                'email/handling_request_handler_parking_confirmation.html',
                {
                    'handling_request': handling_request,
                    'callsign': handling_request.callsign,
                    'aircraft_type': handling_request.aircraft_type.designator,
                    'arrival_date': handling_request.arrival_movement.date_capitalized,
                    'arrival_time': handling_request.arrival_movement.time,
                })

            send_email(
                subject=subject,
                body=body,
                recipient=addresses_to,
                cc=addresses_cc,
                bcc=addresses_bcc,
            )

            handling_request.activity_log.create(
                author_text='System (Auto)',
                details='"Request for Confirmation of Parking Apron & Stand" has been sent',
            )

        notifications = handling_request.notifications
        notifications.is_handler_parking_confirmation_email_sent = True
        notifications.save()

    return True


def send_signed_spf_request(handling_request, author, addresses_cc=None):
    if addresses_cc is None:
        addresses_cc = []

    attachments = []

    if not handling_request.is_gh_signed_spf_request_can_be_sent:
        return handling_request

    requester_position = author.organisation_people.filter(
        organisation_id=100000000).first()

    # Addresses TO
    addresses_to = handling_request.handling_agent.get_email_address()

    # Addresses CC and BCC
    addresses_cc.append('ops@amlglobal.net')
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_signed_spf_request')
    addresses_cc += email_function.get_addresses_cc(handling_request.handling_agent)
    addresses_bcc = email_function.get_addresses_bcc(handling_request.handling_agent)

    # Stop execution in case if no any recipient available
    if not addresses_to and not addresses_cc:
        handling_request.activity_log.create(
            author=author,
            record_slug='spf_gh_request_email_not_sent',
            details='Auto-generated Request Signed SPF email has not been sent as no any recipient available',
        )
        return None

    arrival_date = handling_request.arrival_movement.date.strftime("%Y-%m-%d")
    departure_date = handling_request.departure_movement.date.strftime("%Y-%m-%d")
    aircraft_type_designator = handling_request.aircraft_type.type_designator.icao

    subject = ('Request for Signed SPF Document - {location} - {callsign} ({aircraft_designator}) '
               '- {arrival_date} / {departure_date}').format(
        location=handling_request.location_short_repr,
        aircraft_designator=handling_request.aircraft_type.designator,
        callsign=handling_request.callsign,
        arrival_date=arrival_date,
        departure_date=departure_date,

    )

    body = render_to_string(
        template_name='email/gh_signed_spf_request.html',
        context={
            'requester_person': author,
            'requester_position': requester_position,
            'handling_request': handling_request,
            'aircraft_type_designator': aircraft_type_designator,
            'arrival_date': arrival_date,
            'departure_date': departure_date,
            'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            'url': reverse_lazy('admin:handling_request_upload_signed_spf', kwargs={'uuid': handling_request.uuid}),
        }
    )

    auto_spf_attachment = handling_request.get_spf_pdf()
    attachments.append(auto_spf_attachment)

    send_email.delay(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )

    handling_request.notifications.is_spf_gh_request_email_sent = True
    handling_request.notifications.save()

    handling_request.activity_log.create(
        author=author,
        record_slug='spf_gh_request_email_sent',
        details=f'Auto-generated Request Signed SPF email sent to {handling_request.handling_agent.full_repr}',
        data={'handler_name': handling_request.handling_agent.full_repr,
              'handler_id': handling_request.handling_agent.pk}
    )

    return handling_request
