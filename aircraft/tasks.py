import os
import string
from django.db.models import Q
from django.db.models.functions import Replace
from celery import shared_task


@shared_task
def delete_conflicting_test_aircraft(aircraft_pk, ads_asn, registration):
    """
    Removes test aircraft where the ads_asn or registration may conflict with
    newly saved details (test aircraft are normally hidden/ignored and conflicts
    with them are intentionally not picked up during validation).
    """
    from .models import Aircraft

    registration_without_punctuation = registration.translate(
        str.maketrans('', '', string.punctuation)).lower()

    test_aircraft = Aircraft.objects.get_test_aircraft()

    test_registrations = test_aircraft.values_list('pk', 'details__registration')
    test_ids_w_matching_registration = []

    for item in test_registrations:
        reg_wo_punctuation = item[1].translate(str.maketrans('', '', string.punctuation)).lower()

        if reg_wo_punctuation == registration_without_punctuation:
            test_ids_w_matching_registration.append(item[0])

    aircraft_to_delete = test_aircraft.filter(
        Q(ads_asn=ads_asn) |
        Q(pk__in=test_ids_w_matching_registration)
    ).exclude(pk=aircraft_pk)

    aircraft_to_delete.delete()
