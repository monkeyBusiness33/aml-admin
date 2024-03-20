from django import template
from handling.models import HandlingRequestServices

register = template.Library()


@register.filter(takes_context=True)
def get_handling_request_service_arrival_details(handling_request, service):
    qs = HandlingRequestServices.objects.filter(
        movement__request=handling_request,
        movement__direction__code='ARRIVAL',
        service=service,
    )
    handling_request_service = qs.first()
    return handling_request_service


@register.filter(takes_context=True)
def get_handling_request_service_departure_details(handling_request, service):
    qs = HandlingRequestServices.objects.filter(
        movement__request=handling_request,
        movement__direction__code='DEPARTURE',
        service=service,
    )
    handling_request_service = qs.first()
    return handling_request_service
