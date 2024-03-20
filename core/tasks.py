import socket

from celery import shared_task
from celery.utils.log import get_task_logger
from app.celery import app as celery_app
from celery.schedules import crontab
from django.conf import settings
from firebase_admin.messaging import Aps, Message, Notification
from firebase_admin._messaging_utils import APNSConfig, APNSPayload

from core.utils.helpers import normalize_phone_number
from user.models import User
from django.core.mail import EmailMessage
from django.conf import settings
from email.mime.image import MIMEImage
import os
from organisation.utils.ofac_api_pooler import organisations_ofac_status_update
from twilio.rest import Client
import sentry_sdk

from user.utils.people_travel_documents import process_travel_documents_validity

logger = get_task_logger(__name__)


@shared_task
def send_push(title: str = None, body: str = None, data: dict = {}, users: list = None):
    """
    Generic function for push notifications
    :param title: Title of the push message
    :param body: Body of the push message
    :param data: Tech data, required to show notification when app in background
    :param users: QuerySet on function call or list of user's pk if function called with .delay()
    :return:
    """
    notification_message = None
    if title and body:
        notification_message = Notification(title=title, body=body)

    if users:
        for user in users:
            if not user:
                continue
            if not isinstance(user, User):
                user = User.objects.get(pk=user)

            # Disable push notification for any user except 'is_staff' in DEBUG mode.
            # if settings.DEBUG and not user.is_staff:
            #     logger.warning(f'Push message sending interrupted in DEBUG mode (User ID: {user.pk})')
            #     continue

            for device in user.fcmdevice_set.filter(active=True).all():
                device.send_message(
                    Message(
                        notification=notification_message,
                        data=data,
                        apns=APNSConfig(
                            payload=APNSPayload(
                                aps=Aps(content_available=True)
                            )),
                    )
                )


@shared_task
def send_whatsapp_message(body: str = '', recipients: list = None):
    """
    Send WhatsApp message using Twilio API
    :param body: String of message body
    :param recipients: List of phone numbers
    :return:
    """
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    whatsapp_sender = f'whatsapp:{settings.TWILIO_SENDER_NUMBER}'

    for recipient in recipients:
        if recipient:
            recipient = normalize_phone_number(phone_number=recipient)
            twilio_client.messages.create(
                from_=whatsapp_sender,
                to=f'whatsapp:{recipient}',
                body=body,
            )


def get_valid_email_addresses(addresses: list):
    """
    Validate list of email addresses (or string with single email address)
    :param addresses:
    :return: Ready to use list of email addresses
    """
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    validated_addresses = []

    if not isinstance(addresses, list):
        addresses = [addresses]

    for address in addresses:
        try:
            validate_email(address)
            if address not in validated_addresses:
                validated_addresses.append(address)
        except ValidationError:
            pass

    return validated_addresses


@shared_task
def send_email(subject, body, recipient: list = [], sender=None, reply_to=None, cc: list = [], bcc: list = [],
               images=None, attachments=None):

    # Filter only valid email addresses to avoid issues with "None" and so on
    recipient = get_valid_email_addresses(recipient)
    cc = get_valid_email_addresses(cc)
    bcc = get_valid_email_addresses(bcc)

    if not images:
        images = {}

    if not recipient and not cc and not bcc:
        sentry_sdk.capture_message("Email Message has no any recipient to deliver", "info")
        return False

    msg = EmailMessage(
        subject,
        body,
        sender if sender else settings.EMAIL_FROM_ADDRESS,
        recipient,
        reply_to=reply_to,
        cc=cc,
        bcc=bcc,
    )
    msg.content_subtype = 'html'
    msg.mixed_subtype = 'related'
    img_path = os.path.join(settings.BASE_DIR, 'app/static/assets/img/aml_logo.png')
    with open(img_path, 'rb') as f:
        logo = MIMEImage(f.read())
        f.close()
        logo.add_header('Content-ID', '<aml_logo.png>')
        msg.attach(logo)
    if images:
        for image_name, image_path in images.items():
            img_path = os.path.join(settings.BASE_DIR, image_path)
            with open(img_path, 'rb') as f:
                img = MIMEImage(f.read())
                f.close()
                img.add_header('Content-ID', f'<{image_name}>')
                msg.attach(img)

    if attachments:
        for attachment in attachments:
            msg.attach(attachment['name'], attachment['content'], attachment['type'])

    msg.send(fail_silently=False)


@shared_task
def update_database_sequences_task():
    from .utils.database_maintenance import update_database_sequences
    update_database_sequences()


@shared_task
def daily_system_tasks():
    """
    Include here all daily tasks which will be executed right after midnight
    :return:
    """
    process_travel_documents_validity()


# Run scheduler only if it enabled and server hostname allowed to do background jobs
if settings.BACKGROUND_SCHEDULER and settings.BACKGROUND_SCHEDULER_HOST == socket.gethostname():
    celery_app.conf.beat_schedule = {
        # 'sync_ads_data': {
        #     'task': 'ads_bridge.tasks.sync_ads_all',
        #     'schedule': crontab(),
        #     'options': {
        #             'expires': 60,
        #     },
        # },
        'send_missed_push_notifications': {
            'task': 'handling.tasks.send_missed_push_notifications',
            'schedule': crontab(),
            'options': {
                'expires': 60,
            },
        },
        'organisations_ofac_status_update': {
            'task': 'organisation.utils.ofac_api_pooler.organisations_ofac_status_update',
            'schedule': crontab(minute=10, hour=1),
            'options': {
                'expires': 60,
            },
        },
        'update_database_sequences_task': {
            'task': 'core.tasks.update_database_sequences_task',
            'schedule': crontab(minute=0, hour='*/3'),
            'options': {
                'expires': 60,
            },
        },
        'run_dla_scraper_task': {
            'task': 'dla_scraper.tasks.run_dla_scraper_task',
            'schedule': crontab(minute=30, hour='6,18'),
            'options': {
                'expires': 60,
            },
        },
        'check_previous_scraper_run': {
            'task': 'dla_scraper.tasks.check_previous_scraper_run',
            'schedule': crontab(minute=30, hour='*'),
            'options': {
                'expires': 60,
            },
        },
        'handler_parking_confirmation_email': {
            'task': 'handling.tasks.handler_parking_confirmation_notification',
            'schedule': crontab(minute='*/1'),
            'options': {
                'expires': 60,
            },
        },
        'daily_system_tasks': {
            'task': 'core.tasks.daily_system_tasks',
            'schedule': crontab(minute=1, hour=0),
            'options': {
                'expires': 60,
            },
        },
        'pricing_update_fuel_agreement_active_status': {
            'task': 'pricing.tasks.pricing_update_fuel_agreement_active_status_task',
            'schedule': crontab(minute=0, hour=0),
            'options': {
                'expires': 86400,
            },
        },
        'pricing_update_fuel_index_pricing_active_status_task': {
            'task': 'pricing.tasks.pricing_update_fuel_index_pricing_active_status_task',
            'schedule': crontab(minute=0, hour=0),
            'options': {
                'expires': 86400,
            },
        }
    }
