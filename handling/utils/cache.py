from django.utils import timezone
from app.celery import app
from django.core.cache import cache


def handling_request_cache_invalidation(handling_request):
    from handling.tasks import handling_request_invalidate_cache_task
    cache_key_base = f'sfr_{handling_request.id}_invalidate_cache_task'

    if handling_request.get_etd_date() > timezone.now():
        cache_key_departure = cache_key_base + '_departure'

        # Cancel existing task
        app.control.revoke(cache.get(cache_key_departure, None))

        # Add task to invalidate cached on ETD date
        celery_task = handling_request_invalidate_cache_task.apply_async(
            args=(handling_request.pk,), eta=handling_request.get_etd_date())

        # Save new id of the task
        cache.set(cache_key_departure, celery_task.id, timeout=None)

    if handling_request.get_eta_date() > timezone.now():
        cache_key_arrival = cache_key_base + '_arrival'

        # Cancel existing task
        app.control.revoke(cache.get(cache_key_arrival, None))

        # Add task to invalidate cached on ETA date
        celery_task = handling_request_invalidate_cache_task.apply_async(
            args=(handling_request.pk,), eta=handling_request.get_eta_date())

        # Save new id of the task
        cache.set(cache_key_arrival, celery_task.id, timeout=None)
