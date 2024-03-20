from handling.models import HandlingService, HandlingRequestServices


def mission_leg_passengers_handling_service(mission_leg, author=None):
    passengers_handling_service = HandlingService.objects.filter(
        is_active=True,
        codename='passengers_handling',
    ).first()

    # Update Departure services for previous leg
    if mission_leg.previous_leg and mission_leg.previous_leg.arrival_aml_service \
            and hasattr(mission_leg.previous_leg, 'turnaround'):
        if mission_leg.pob_pax is not None:
            mission_leg.previous_leg.turnaround.requested_services.update_or_create(
                service=passengers_handling_service,
                defaults={
                    'on_departure': True,
                    'updated_by': author,
                },
            )
        elif mission_leg.pob_pax is None and mission_leg.previous_leg.pob_pax is None:
            mission_leg.previous_leg.turnaround.requested_services.filter(service=passengers_handling_service).delete()

    # Update services for current flight leg
    on_arrival = True if mission_leg.pob_pax is not None else False
    if hasattr(mission_leg, 'next_leg') and mission_leg.next_leg.pob_pax:
        on_departure = True if mission_leg.next_leg.pob_pax is not None else False
    else:
        on_departure = False

    if mission_leg.arrival_aml_service and hasattr(mission_leg, 'turnaround'):
        if on_arrival or on_departure:
            mission_leg.turnaround.requested_services.update_or_create(
                service=passengers_handling_service,
                defaults={
                    'on_arrival': on_arrival,
                    'on_departure': on_departure,
                    'updated_by': author,
                },
            )
        else:
            mission_leg.turnaround.requested_services.filter(service=passengers_handling_service).delete()


def mission_leg_cargo_service(mission):
    cargo_service = HandlingService.objects.filter(
        is_active=True,
        codename='cargo_loading_unloading',
    ).first()

    if not cargo_service:
        return

    for turnaround in mission.turnarounds.order_by('mission_leg__sequence_id'):
        previous_leg = turnaround.mission_leg.previous_leg
        current_leg = turnaround.mission_leg
        next_leg = getattr(turnaround.mission_leg, 'next_leg', None)

        if current_leg.cob_lbs and next_leg.cob_lbs != current_leg.cob_lbs:
            on_arrival = True
        else:
            on_arrival = False

        if next_leg and next_leg.cob_lbs and next_leg.cob_lbs != current_leg.cob_lbs:
            on_departure = True
        else:
            on_departure = False

        if on_arrival or on_departure:
            turnaround.requested_services.update_or_create(
                service=cargo_service,
                defaults={
                    'on_arrival': on_arrival,
                    'on_departure': on_departure,
                    'updated_by': mission.updated_by,
                },
            )
        else:
            turnaround.requested_services.filter(service=cargo_service).delete()

        if not on_arrival:
            qs = HandlingRequestServices.objects.filter(
                movement__direction_id='ARRIVAL',
                movement__request__mission_turnaround=turnaround,
                service=cargo_service
            )
            for service in qs:
                service.delete()

        if not on_departure:
            qs = HandlingRequestServices.objects.filter(
                movement__direction_id='DEPARTURE',
                movement__request__mission_turnaround=turnaround,
                service=cargo_service
            )
            for service in qs:
                service.delete()
