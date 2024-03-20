from datetime import datetime
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from core.tasks import send_email

from dod_portal.utils.dod_user_utils import invite_dod_user, reset_dod_user_password


def invite_ops_portal_user(user):
    person_details = getattr(user.person, 'details')

    if person_details and user.is_staff:
        subject = f'AML Ops Portal Invitation'
        body = render_to_string(
            'email/ops_portal_invitation.html',
            {
                'user': user,
                'person_details': person_details,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            })

        app_images = {
            'play-market.png': 'app/static/assets/img/google-play-button.png',
            'appstore.png': 'app/static/assets/img/appstore-button.png'
        }

        send_email.delay(
            subject=subject,
            body=body,
            recipient=person_details.contact_email,
            images=app_images,
        )
        user.is_invitation_sent = True
        user.last_token_sent_at = datetime.now()
        user.is_forced_onboard = True  # Force user to pass onboarding
        user.save()


def reset_ops_user_password(user):
    person_details = getattr(user.person, 'details', None)

    if person_details and user.is_staff:
        subject = f'AML Ops Portal Password Reset URL'
        body = render_to_string(
            'email/ops_portal_password_reset.html',
            {
                'person_details': person_details,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'domain': settings.AML_OPERATIONS_PORTAL_DOMAIN,
            })

        send_email.delay(
            subject=subject,
            body=body,
            recipient=person_details.contact_email,
        )

        user.last_token_sent_at = datetime.now()
        user.save()


def invite_external_user(user):
    """Function send user invitation email regarding user account type

    Args:
        user (obj): User object with associated Person
    """
    # Send invitation only in case when it hasn't already sent
    if not user.is_invitation_sent:
        if user.is_dod_portal_user:
            # DoD style invitation
            invite_dod_user(user)
        if user.is_staff:
            # Ops style invitation
            invite_ops_portal_user(user)


def reset_external_user_password(user):
    if user.is_staff:
        reset_ops_user_password(user)
    if user.is_dod_portal_user:
        reset_dod_user_password(user)
