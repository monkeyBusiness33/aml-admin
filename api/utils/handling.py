import ast
from django.db.models.query_utils import Q
from rest_framework import serializers
from handling.models import HandlingService, HandlingRequestServices, HandlingRequestMovement


def handling_reqeust_create_service_booking(services: list,
                                            movement: HandlingRequestMovement,
                                            handling_request,
                                            amend: bool = False,
                                            person: object = None):
    # Remove requested services from the HandlingRequest
    if amend:
        services_ids = [ast.literal_eval(service_entry)['service_id']
                        for service_entry in services if 'service_id' in ast.literal_eval(service_entry)]

        absent_services = movement.hr_services.exclude(
            Q(service_id__in=services_ids) |
            Q(service__always_included=True)
            ).all()
        if absent_services.exists():
            for service in absent_services:
                service.updated_by = person
                service.delete()
            handling_request.is_services_amended = True

    # Add new services to the HandlingReqeust
    for service_entry in services:
        service_entry = ast.literal_eval(service_entry)
        service_id = service_entry.get('service_id')
        booking_text = None
        booking_quantity = None

        service = HandlingService.objects.filter(pk=service_id).first()
        if not service:
            raise serializers.ValidationError(
                detail='Invalid Service id submitted', code='invalid_value')

        if service.is_allowed_free_text:
            booking_text = service_entry.get('booking_text', None)
        elif service.is_allowed_quantity_selection:
            booking_quantity = service_entry.get('booking_quantity', None)

        booking_note = service_entry.get('note', None)

        if all([booking_text, booking_quantity]):
            raise serializers.ValidationError(
                detail='Both "Text Requirements" and "Service Quantity" are submitted, should be one of them',
                code='invalid_value')

        if not movement.hr_services.filter(service_id=service_id).exists():
            hr_service = HandlingRequestServices.objects.create(service_id=service_id,
                                                                booking_text=booking_text,
                                                                booking_quantity=booking_quantity,
                                                                note=booking_note,
                                                                movement=movement,
                                                                updated_by=person,
                                                                )
            if amend:
                handling_request.is_services_amended = True
        else:
            for service in movement.hr_services.filter(service_id=service_id):
                service.booking_text = booking_text
                service.booking_quantity = booking_quantity
                service.note = booking_note
                service.booking_confirmed = None
                service.updated_by = person
                service.save()
                if service.is_amended:
                    handling_request.is_services_amended = True

    return handling_request
