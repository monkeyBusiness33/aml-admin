from django.db.models import Q


def sync_dla_services_to_handling_services(dla_service_id=None):
    filter_q = Q(pk=dla_service_id) if dla_service_id else Q()
    from organisation.models import DlaService
    dla_services = DlaService.objects.filter(filter_q)

    for dla_service in dla_services:
        from handling.models import HandlingService
        HandlingService.objects.filter(
            Q(dla_service_id=dla_service.pk) | Q(name=dla_service.name)
        ).exclude(custom_service_for_request__isnull=False).update_or_create(
            defaults={
                'name': dla_service.name,
                'dla_service': dla_service,
                'is_dla_v2': True,
                'is_spf_v2_visible': dla_service.is_spf_included,
                'is_dla_v2_visible_arrival': dla_service.is_dla_visible_arrival,
                'is_dla_v2_visible_departure': dla_service.is_dla_visible_departure,
            }
        )
