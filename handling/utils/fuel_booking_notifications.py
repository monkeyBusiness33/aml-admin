from celery import shared_task
from django.template.loader import render_to_string
from ..models import HandlingRequest
from core.tasks import send_email


@shared_task
def staff_fuel_booking_cancelled_notification(handling_request, amendment=None):
    """
    Function send "CANCELLED DoD Fuel Order" email notification to the fuel team
    :param handling_request: HandlingRequest instance or PK
    :param amendment: Is fuel amended
    :return:
    """
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.filter(pk=handling_request).first()

    # Stop execution if S&F Request have no fuel requested and not amended
    if not handling_request.fuel_required and not amendment:
        return None

    fuel_order_number = ''
    if hasattr(handling_request, 'fuel_booking'):
        fuel_order_number = f'{handling_request.fuel_booking.fuel_order_number or "DLA Contracted Location"}'

    subject = 'CANCELLED - DoD Fuel Order - {callsign} / {location} / {arrival_datetime}Z {fuel_order_number}'.format(
        callsign=handling_request.callsign,
        location=handling_request.location_tiny_repr,
        arrival_datetime=handling_request.arrival_movement.date.strftime("%b-%d-%Y %H:%M"),
        fuel_order_number=f'/ {fuel_order_number}' if fuel_order_number else '',
    )
    body = render_to_string(
        template_name='email/dod_fuel_order_cancelled.html',
        context={
            'amendment': amendment,
            'handling_request': handling_request,
            'fuel_order_number': fuel_order_number,
        }
    )

    send_email(
        subject=subject,
        body=body,
        recipient=['fuelteam@amlglobal.net'],
    )
