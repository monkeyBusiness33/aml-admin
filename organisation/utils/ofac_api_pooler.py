from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, DateField, Case, When, OuterRef, Exists
from django.conf import settings
from core.utils.ofac_api import OfacApi
from ..models import Organisation
from django.utils import timezone
from celery import shared_task


@shared_task
def organisations_ofac_status_update(requests_limit=950):
    requests_count = 0
    status_registered_name = None
    status_trading_name = None
    ofac = OfacApi(api_key=settings.OFAC_API_KEY, min_score=95)
    organisations = Organisation.objects.filter(
        Q(ofac_excepted=None) & (Q(details__type_id__in=[1, 2, 5, 11, 13]) | Q(operator_details__isnull=False)
                                 | Q(oilco_details__isnull=False) | Q(trip_support_clients__isnull=False))
    ).order_by(F('ofac_latest_update').asc(nulls_first=True)).distinct()[:requests_limit]

    for organisation in organisations:
        # Search using registered name

        status_registered_name = ofac.search_by_name(
            organisation.details.registered_name, 'Entity')
        requests_count += 1

        if organisation.details.trading_name:
            # Try to search using trading name

            status_trading_name = ofac.search_by_name(
                organisation.details.trading_name, 'Entity')
            requests_count += 1

        ofac_status = any([status_registered_name, status_trading_name])
        organisation.is_sanctioned_ofac = ofac_status
        organisation.ofac_latest_update = timezone.now()
        organisation.save()

        if requests_count >= requests_limit:
            break
