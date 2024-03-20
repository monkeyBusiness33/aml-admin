from datetime import datetime
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from core.tasks import send_email


def reset_dod_user_password(user):
    person_details = getattr(user.person, 'details', None)

    if person_details and user.is_dod_portal_user:
        subject = f'DoD Flight Servicing Portal Password Reset'
        body = render_to_string(
            'dod/email/password_reset_email.html',
            {
                'person_details': person_details,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'domain': settings.AML_DOD_PORTAL_DOMAIN,
            })

        send_email.delay(
            subject=subject,
            body=body,
            recipient=person_details.contact_email,
        )

        user.last_token_sent_at = datetime.now()
        user.save()


def invite_dod_user(user):
    person_details = getattr(user.person, 'details')
    
    if person_details and user.is_dod_portal_user:
        subject = f'DoD Flight Servicing Portal Invitation'
        body = render_to_string(
            'dod/email/dod_user_invitation.html',
            {
                'user': user,
                'person_details': person_details,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'domain': settings.AML_DOD_PORTAL_DOMAIN,
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
        user.save()
