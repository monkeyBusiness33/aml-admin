from tempfile import NamedTemporaryFile

from pypdf import PdfWriter, PdfReader, Transformation
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from datetime import datetime

from core.tasks import send_email, send_push
from organisation.models import EmailFunction


def sign_document(signature, document, author):
    static_path = f'file://{settings.BASE_DIR}/app/static'
    template_name = 'handling_request_document_sign/signature_overlay_v1.html'

    # Create signature layer
    context = {
        'static_path': static_path,
        'author': author,
        'signature_file': signature.name,
        'signing_datetime': datetime.now().strftime("%d-%b-%Y"),
    }

    signature_layer_html = HTML(string=render_to_string(template_name, context))
    signature_layer_pdf_obj = signature_layer_html.render()
    signature_layer_pdf_bytes = signature_layer_pdf_obj.write_pdf()

    signature_layer_pdf_file = NamedTemporaryFile()
    signature_layer_pdf_file.write(signature_layer_pdf_bytes)
    signature_layer_pdf_file.seek(0)

    signature_layer_pdf_page = PdfReader(signature_layer_pdf_file).pages[0]

    # Sign the given document
    writer = PdfWriter()
    reader = PdfReader(document.recent_file.file)
    content_page = reader.pages[0]
    content_page.merge_transformed_page(
        signature_layer_pdf_page,
        Transformation(),
    )
    writer.add_page(content_page)

    signed_pdf_file = NamedTemporaryFile()
    writer.write(signed_pdf_file)
    signed_pdf_file.seek(0)

    # Generate file name
    document_name = document.recent_file.file.name.split('.')[0]
    resulting_file_name = f'{document_name}_signed.pdf'

    file_dict = {
        'name': resulting_file_name,
        'file': signed_pdf_file,
        'content': signed_pdf_file.read(),
        'type': 'application/pdf',
    }

    return file_dict


#############################################
# Singed invoice notifications
#############################################


def invoice_signing_email_notification(document):
    organisation = document.handling_request.customer_organisation

    attachments = []

    # Addresses TO
    authorising_people = organisation.organisation_people.filter(is_authorising_person=True)
    addresses_to = list(authorising_people.values_list('contact_email', flat=True))

    # Addresses CC and BCC
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_invoice_signed')
    addresses_cc = email_function.get_addresses_cc(organisation)
    addresses_cc += ['avpos.processing@amlglobal.net', 'ops@amlglobal.net', ]
    addresses_bcc = email_function.get_addresses_bcc(organisation)

    subject = 'Signature of AML Global Servicing Invoice by Crew Member - {callsign} - {location} - ' \
              '{departure_date}'.format(
                location=document.handling_request.location_short_repr,
                callsign=document.handling_request.callsign,
                departure_date=document.handling_request.departure_movement.date.strftime("%Y-%m-%d"),
                )

    body = render_to_string(
        template_name='email/invoice_signature_notification.html',
        context={
            'document': document,
            'authorising_people': authorising_people,
            'handling_request': document.handling_request,
        }
    )

    attachment = {
        'name': document.recent_file.file.name,
        'content': document.recent_file.file.read(),
        'type': 'application/pdf',
    }
    attachments.append(attachment)

    send_email(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )


def invoice_signing_push_notification(document):
    if document.type_id != 10:
        return False

    organisation = document.handling_request.customer_organisation
    authorising_people = organisation.organisation_people.filter(is_authorising_person=True)
    users_to_notify = list(authorising_people.values_list('person__user', flat=True))

    # Send push notification
    if users_to_notify:
        send_push.delay(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=document.handling_request.callsign,
                location=document.handling_request.location_tiny_repr,
                arrival_date=document.handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='The AML Global ground servicing invoice for this turnaround has been signed by {signed_by} '
                 'at {signed_at}. You have been emailed a copy of the signed invoice, and can also view this document '
                 'in the corresponding Servicing & Fueling Request Details screen in the AML Global mobile app.'.format(
                signed_by=document.recent_file.signed_by.full_repr,
                signed_at=document.recent_file.signed_at.strftime("%H:%MZ %b-%d-%Y"),
            ),
            data={
                'handling_request_id': str(document.handling_request.id),
            },
            users=list(users_to_notify)
        )
    return True


#############################################
# Signable invoice notifications
#############################################


def signable_invoice_uploaded_push_notification(document):
    if document.type_id != 10 or not document.handling_request:
        return False

    users_to_notify = document.mission_invoice_notification_people().filter(
        person__user__isnull=False).values_list('person__user', flat=True)

    # Send push notification
    if users_to_notify:
        send_push.delay(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=document.handling_request.callsign,
                location=document.handling_request.location_tiny_repr,
                arrival_date=document.handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='A new ground servicing invoice has been uploaded for this turnaround. '
                 'Please digitally sign this invoice within the next 48 hours by visiting '
                 'the Servicing & Fueling request screen and opening the document titled "{title}"'.format(
                title=document.description,
            ),
            data={
                'handling_request_id': str(document.handling_request.id),
            },
            users=list(users_to_notify)
        )
    return True


def signable_invoice_chase_push_notification(document):
    if document.type_id != 10 or not document.handling_request:
        return False

    if document.is_signed:
        return True

    users_to_notify = document.mission_invoice_notification_people().filter(
        person__user__isnull=False).values_list('person__user', flat=True)

    # Send push notification
    if users_to_notify:
        send_push.delay(
            title='{callsign} / {location} / {arrival_date}'.format(
                callsign=document.handling_request.callsign,
                location=document.handling_request.location_tiny_repr,
                arrival_date=document.handling_request.arrival_movement.date.strftime("%b-%d-%Y"),
            ),
            body='This is a polite reminder to digitally sign the ground servicing invoice for this turnaround at your '
                 'earliest convenience by visiting the Servicing & Fueling request screen and opening the '
                 'document titled "{title}"'.format(
                title=document.description,
            ),
            data={
                'handling_request_id': str(document.handling_request.id),
            },
            users=list(users_to_notify)
        )
    return True


def signable_invoice_chase_email_notification(document):
    if document.type_id != 10 or not document.handling_request:
        return False

    if document.is_signed:
        return True

    people_to_notify_ids = document.mission_invoice_notification_people().values_list('person', flat=True)
    people_to_notify = document.handling_request.customer_organisation.organisation_people.filter(
        person__in=people_to_notify_ids
    )

    # Addresses TO
    addresses_to = list(people_to_notify.values_list('contact_email', flat=True))

    # Addresses CC and BCC
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_invoice_signable')
    addresses_cc = email_function.get_addresses_cc(document.handling_request.customer_organisation)
    addresses_cc += ['ops@amlglobal.net', ]
    addresses_bcc = email_function.get_addresses_bcc(document.handling_request.customer_organisation)

    attachments = []

    subject = 'Please Sign Ground Servicing Invoice - {callsign} - {location} - ' \
              '{arrival_date} / {departure_date}'.format(
                location=document.handling_request.location_short_repr,
                callsign=document.handling_request.callsign,
                arrival_date=document.handling_request.arrival_movement.date.strftime("%Y-%m-%d"),
                departure_date=document.handling_request.departure_movement.date.strftime("%Y-%m-%d"),
                )

    body = render_to_string(
        template_name='email/invoice_signature_chase_notification.html',
        context={
            'document': document,
            'people_to_notify': people_to_notify,
            'handling_request': document.handling_request,
        }
    )

    attachment = {
        'name': document.recent_file.file.name,
        'content': document.recent_file.file.read(),
        'type': 'application/pdf',
    }
    attachments.append(attachment)

    send_email(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )
