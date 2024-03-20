from django.db.models import Count, Q

from handling.models import HandlingRequest
from handling.utils.email_diff_generator import generate_diff_dict


def passengers_payload_update_movements(handling_request, author):
    passengers = handling_request.passengers_payloads.aggregate(
        arrival_passengers=Count('id', filter=Q(is_arrival=True)),
        departure_passengers=Count('id', filter=Q(is_departure=True)),
    )

    old_instance_diff = generate_diff_dict(handling_request=handling_request)

    for movement in handling_request.movement.all():
        is_passengers_amended = movement.passengers != passengers['arrival_passengers'] or \
                                movement.passengers != passengers['departure_passengers']

        if movement.direction.code == 'ARRIVAL' and is_passengers_amended:
            movement.updated_by = author
            movement.is_passengers_onboard = True
            movement.is_passengers_tbc = False
            movement.passengers = passengers['arrival_passengers']
            movement.supress_amendment_notifications = True
            movement.save()

        if movement.direction.code == 'DEPARTURE' and is_passengers_amended:
            movement.updated_by = author
            movement.is_passengers_onboard = True
            movement.is_passengers_tbc = False
            movement.passengers = passengers['departure_passengers']
            movement.supress_amendment_notifications = True
            movement.save()

    # Reset S&F Request handling confirmation status
    if handling_request.is_movement_amended:
        handling_request.supress_amendment_notifications = False
        handling_request.old_instance_diff = old_instance_diff
        handling_request.is_handling_confirmed = False
        handling_request.updated_by = author
        handling_request.save()


def cargo_payload_auto_services(handling_request):
    from handling.models import HandlingService
    cargo_service = HandlingService.objects.filter(
        is_active=True,
        codename='cargo_loading_unloading',
    ).first()

    if not cargo_service:
        return

    if handling_request.payload_cargo_arrival != handling_request.payload_cargo_departure:
        handling_request.arrival_movement.hr_services.update_or_create(service=cargo_service)
        handling_request.departure_movement.hr_services.update_or_create(service=cargo_service)
