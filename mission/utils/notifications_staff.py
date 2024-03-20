from celery import shared_task
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from notifications.signals import notify

from core.tasks import send_email, send_push, send_whatsapp_message
from user.models import User, Person


@shared_task
def mission_submitted_staff_notifications(mission):
    """
    :param mission: Mission
    :return:
    """
    if not mission.created_by.user.is_staff:

        subject = 'New Mission - {mission_number} - {callsign} - {start_date}'.format(
            mission_number=mission.mission_number_repr,
            callsign=mission.callsign,
            start_date=mission.start_date.strftime("%b-%d-%Y"),
        )
        body = render_to_string(
            'email/mission_submitted_staff_email.html',
            {
                'mission': mission,
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
                'mission_url': reverse('admin:missions_details', kwargs={'pk': mission.pk}),
            })

        send_email.delay(
            subject=subject,
            body=body,
            recipient=['ops@amlglobal.net'],
        )

        # Send WhatsApp notification for "Urgent Mission"
        mission_legs_with_servicing = mission.active_legs.filter(arrival_aml_service=True)
        if mission.is_urgent and mission_legs_with_servicing.exists():

            # Create list with servicing locations identifiers
            servicing_locations_identifiers = []
            for mission_leg in mission_legs_with_servicing:
                servicing_locations_identifiers.append(mission_leg.arrival_location.tiny_repr)

            whatsapp_body = 'A new urgent mission has been confirmed: \n\n' \
                            'Mission Start: {mission_start} \n' \
                            'Mission End: {mission_end} \n' \
                            'AML servicing has been requested at: {servicing_at} \n\n' \
                            'Please access this mission through the Missions page in the Operations Portal. \n' \
                            'This is an automated message, please do not reply.'.format(
                                mission_start=mission.start_date.strftime("%b-%d-%Y %H:%M"),
                                mission_end=mission.end_date.strftime("%b-%d-%Y %H:%M"),
                                servicing_at=', '.join(servicing_locations_identifiers),
                            )

            # Send message to all users with "Military Team" role
            military_team_phones = Person.objects.filter(
                user__roles=1000).values_list('details__contact_phone', flat=True)
            if military_team_phones:
                send_whatsapp_message(whatsapp_body, military_team_phones)


@shared_task()
def mission_cancelled_staff_notifications(mission):
    """
    Generate and send all required staff notification on Mission cancellation
    :param mission: HandlingRequest instance or int PK
    :return:
    """
    updated_by = getattr(mission, 'updated_by', '')
    notification_staff_users = list(User.objects.filter(roles=1000).values_list('pk', flat=True).all())

    if updated_by.is_aml_staff:
        author_repr = f'{updated_by.fullname}'
    else:
        author_repr = f'{updated_by.fullname} from {mission.organisation.details.registered_name}'

    notify.send(
        mission,
        recipient=User.objects.filter(roles=1000).all(),
        verb='Mission Cancelled',
        description='<a href="{url}">Mission #{mission_number}</a> has been cancelled'.format(
            url=mission.get_absolute_url(),
            mission_number=mission.mission_number_repr,
        ),
    )

    send_push.delay(
        title=f'CANCELLED - Mission {mission.mission_number_repr} - {mission.start_date.strftime("%b-%d-%Y %H:%M")}Z',
        body='{author_repr} cancelled Mission {mission_number} - {callsign} - {start_date}Z'.format(
            author_repr=author_repr,
            mission_number=mission.mission_number_repr,
            callsign=mission.callsign,
            start_date=mission.start_date.strftime("%b-%d-%Y %H:%M"),
        ),
        data={'mission_id': str(mission.pk)},
        users=notification_staff_users
    )

    subject = 'CANCELLED - Mission {mission_number} - {callsign} - {start_date}Z'.format(
        mission_number=mission.mission_number_repr,
        callsign=mission.callsign,
        start_date=mission.start_date.strftime("%b-%d-%Y %H:%M"),
    )
    body = render_to_string(
        'email/mission_cancelled_staff_email.html',
        {
            'mission': mission,
            'author': updated_by if updated_by else mission.requesting_person,
            'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            'mission_url': mission.get_absolute_url(),
        })

    send_email.delay(
        subject=subject,
        body=body,
        recipient=['ops@amlglobal.net'],
    )


@shared_task()
def notifications_staff_mission_document_uploaded(document_id):
    """
    Staff notification on new mission document upload
    :param document_id: Uploaded Mission Document PK
    :return:
    """
    import mimetypes
    from handling.models import HandlingRequestDocument

    attachments = []
    document = HandlingRequestDocument.objects.get(pk=document_id)

    # Cancel in case if document has been uploaded by staff user
    if document.created_by and document.created_by.is_aml_staff:
        return None

    applicability = document.applicability
    if applicability == 'Whole Mission':
        applicability = f'the {applicability}'

    mission = document.document_mission

    subject = ('New Mission Document Upload - {applicability} - {mission_number} - {callsign} - '
               '{start_date}Z / {end_date}Z').format(
        applicability=applicability,
        mission_number=mission.mission_number_repr,
        callsign=mission.callsign,
        start_date=mission.start_date.strftime("%b-%d-%Y %H:%M"),
        end_date=mission.end_date.strftime("%b-%d-%Y %H:%M"),
    )

    body = render_to_string(
        'email/mission_document_uploaded.html',
        {
            'applicability': applicability,
            'document': document,
            'mission': document.document_mission,
        })

    mime_type, encoding = mimetypes.guess_type(document.recent_file.file.name)
    attachment = {
        'name': document.recent_file.file.name,
        'content': document.recent_file.file.read(),
        'type': mime_type,
    }
    attachments.append(attachment)

    send_email(
        subject=subject,
        body=body,
        recipient=['ops@amlglobal.net'],
        attachments=attachments,
    )
