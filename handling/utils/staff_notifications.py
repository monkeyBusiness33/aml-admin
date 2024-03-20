import json

from django.template.loader import render_to_string
from notifications.signals import notify
from core.tasks import send_push, send_email
from handling.utils.email_diff_generator import HandlingRequestDiff
from user.models import User, Person
from django.conf import settings
from django.urls import reverse
from celery import shared_task


@shared_task()
def staff_amendment_notifications(handling_request, amended_fields, author=None):
    """
    Generate and send all required staff notification on S&F Request amendment
    :param handling_request: HandlingRequest instance or int PK
    :param amended_fields: List of dicts of amended data
    :param author: Person instance or int PK
    :return:
    """
    from handling.models import HandlingRequestServices, HandlingRequest
    # Get S&F Request instance if it's PK passed (for Celery)
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.filter(pk=handling_request).first()

    # Get Person instance if it's PK passed (for Celery)
    if author and not isinstance(author, Person):
        author = Person.objects.filter(pk=author).first()

    notification_staff_users = list(User.objects.filter(roles=1000).values_list('pk', flat=True).all())

    if not author:
        author = handling_request.primary_contact

    if author.is_aml_staff:
        author_repr = f'{author.fullname}'
    else:
        author_repr = f'{author.fullname} from {handling_request.customer_organisation.details.registered_name}'

    notify.send(handling_request,
                recipient=User.objects.filter(roles=1000).all(),
                verb='UPDATE Servicing & Fueling Request',
                description='<a href="{url}">S&F Request #{request_id}</a> has been amended'.format(
                    url=handling_request.get_absolute_url(),
                    request_id=handling_request.pk,
                ))

    send_push.delay(
        title=f'UPDATE - {handling_request.callsign} - {handling_request.location_short_repr} amended',
        body='{author_repr} amended servicing & fueling request for {location} - {arrival_date}'.format(
                author_repr=author_repr,
                location=handling_request.location_short_repr,
                arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
                ),
        data={'handling_request_id': str(handling_request.id)},
        users=notification_staff_users
    )

    # Create "Amendment Object"
    handling_request_diff_json = json.loads(amended_fields)
    diff_obj = HandlingRequestDiff(handling_request_diff_json)

    requested_services = HandlingRequestServices.objects.filter(movement__request=handling_request).all()
    subject = 'UPDATE Servicing & Fueling Request - {callsign} / {location} / {arrival_date}Z'.format(
        callsign=handling_request.callsign,
        location=handling_request.location_short_repr,
        arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
    )
    body = render_to_string(
        'email/handling_request_updated.html',
        {
            'handling_request': handling_request,
            'amendment': True,
            'diff_obj': diff_obj,
            'requested_services': requested_services,
            'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            'handling_request_url': reverse('admin:handling_request', kwargs={'pk': handling_request.pk}),
        })

    send_email.delay(
        subject=subject,
        body=body,
        recipient=['ops@amlglobal.net'],
    )


@shared_task()
def staff_cancellation_notifications(handling_request, author=None, auto_cancellation_reason=None):
    """
    Generate and send all required staff notification on S&F Request cancellation
    :param handling_request: HandlingRequest instance or int PK
    :param author: Person instance or int PK
    :param auto_cancellation_reason: str or None
    :return:
    """
    from handling.models import HandlingRequest
    # Get S&F Request instance if it's PK passed (for Celery)
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.filter(pk=handling_request).first()

    # Get Person instance if it's PK passed (for Celery)
    if author and not isinstance(author, Person):
        author = Person.objects.filter(pk=author).first()

    notification_staff_users = list(User.objects.filter(roles=1000).values_list('pk', flat=True).all())

    if not author:
        author = handling_request.primary_contact

    if author.is_aml_staff:
        author_repr = f'{author.fullname}'
    else:
        author_repr = f'{author.fullname} from {handling_request.customer_organisation.details.registered_name}'

    from .fuel_booking_notifications import staff_fuel_booking_cancelled_notification
    staff_fuel_booking_cancelled_notification.delay(handling_request.pk)

    # For mission-generated S&F Requests, send cancellation emails with altered wording
    subject = 'CANCELLED - Servicing & Fueling Request - {callsign} / {location} / {arrival_date}Z'.format(
        callsign=handling_request.callsign,
        location=handling_request.location_short_repr,
        arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
    )
    body = render_to_string(
        'email/handling_request_cancelled.html',
        {
            'handling_request': handling_request,
            'author': author if author else handling_request.primary_contact,
            'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            'handling_request_url': reverse('admin:handling_request', kwargs={'pk': handling_request.pk}),
            'auto_cancellation_reason': auto_cancellation_reason
        })

    send_email.delay(
        subject=subject,
        body=body,
        recipient=['ops@amlglobal.net'],
    )

    # Do not send other notifications for mission generated S&F Request
    if not handling_request.is_standalone:
        return

    notify.send(
        handling_request,
        recipient=User.objects.filter(roles=1000).all(),
        verb='S&F Request Cancelled',
        description='<a href="{url}">S&F Request #{handling_request_id}</a> has been cancelled'.format(
            url=handling_request.get_absolute_url(),
            handling_request_id=handling_request.pk,
        ),
    )

    send_push.delay(
        title=f'CANCELLED - {handling_request.callsign} - {handling_request.location_short_repr}',
        body='{author_repr} cancelled servicing & fueling request for {location} - {arrival_date}'.format(
            author_repr=author_repr,
            location=handling_request.location_short_repr,
            arrival_date=handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
        ),
        data={'handling_request_id': str(handling_request.id)},
        users=notification_staff_users
    )


def spf_submission_staff_notifications(spf_id):
    from handling.models import ServiceProvisionForm
    notification_staff_users = list(User.objects.filter(roles=1000).values_list('pk', flat=True).all())
    spf = ServiceProvisionForm.objects.get(pk=spf_id)

    notify.send(
        spf,
        recipient=User.objects.filter(roles=1000).all(),
        verb='New SPF Submission',
        description='An SPF submission has been received for Handling Request <a href="{url}">#{request_id}</a>'.format(
            url=spf.handling_request.get_absolute_url(),
            request_id=spf.handling_request,
        )
    )

    send_push(
        title='SPF submission for {callsign} - {location} received'.format(
            callsign=spf.handling_request.callsign,
            location=spf.handling_request.location_short_repr,
        ),
        body='An SPF submission has been received for flight {callsign} at {location}'.format(
            callsign=spf.handling_request.callsign,
            location=spf.handling_request.location_short_repr,
        ),
        data={'handling_request_id': str(spf.handling_request.id)},
        users=notification_staff_users
    )


@shared_task()
def staff_aog_notifications(handling_request, author=None):
    """
    Generate and send AOG staff notification
    :param handling_request: HandlingRequest instance
    :param author: Person instance
    :return:
    """
    from chat.utils.conversations import handling_request_create_conversation
    if not handling_request.is_aog:
        return
    system_notifications_person = Person.objects.get(pk=999999999)
    conversation = handling_request_create_conversation(handling_request, author=author)

    conversation.messages.create(
        author=system_notifications_person,
        content='***AIRCRAFT AOG***'
    )
    return True


def notification_staff_signed_spf_uploaded(handling_request):

    subject = 'Signed SPF Submission for S&F Request - {callsign} / {location} / {reference}'.format(
        callsign=handling_request.callsign,
        location=handling_request.location_short_repr,
        reference=handling_request.reference,
    )
    body = render_to_string(
        'email/gh_signed_spf_submitted.html',
        {
            'handling_request': handling_request,
            'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            'handling_request_url': reverse('admin:handling_request', kwargs={'pk': handling_request.pk}),
        })

    send_email.delay(
        subject=subject,
        body=body,
        recipient=['ops@amlglobal.net'],
    )
