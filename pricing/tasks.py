from django.template.loader import render_to_string
from celery import shared_task

from core.tasks import send_email
from pricing.models import FuelIndexPricing
from supplier.models import FuelAgreement
from user.models import Person


@shared_task
def pricing_update_fuel_agreement_active_status_task():
    """
    Update the `is_active` status of all agreements daily based on start / end dates.
    """
    agreements = FuelAgreement.objects.all()

    for agreement in agreements:
        agreement.update_active_status_based_on_date()
        agreement.save(update_fields=['is_active'])


@shared_task
def pricing_update_fuel_index_pricing_active_status_task():
    """
    Update the `is_active` status of all fuel index prices daily based on start / end dates.
    """
    pricing = FuelIndexPricing.objects.all()

    for price in pricing:
        price.update_active_status_based_on_date()
        price.save(update_fields=['is_active'])


@shared_task
def generate_pricing_update_request_email(sender_email, send_to, requesting_person_id, locations_fuel_dict):
    requesting_person = Person.objects.filter(pk=requesting_person_id).first()
    subject = 'Fuel Pricing Update Request - AML Global'

    body = render_to_string(
        template_name='email/supplier_fuel_pricing_update_request.html',
        context={
            'sender_email': sender_email,
            'requesting_person': requesting_person,
            'locations_fuel_dict': locations_fuel_dict,
        }
    )

    send_email(
        sender=sender_email,
        reply_to=[sender_email],
        subject=subject,
        body=body,
        recipient=send_to['to'],
        cc=send_to['cc'],
        bcc=send_to['bcc'],
    )
