from datetime import datetime

from django.db.models import Q

from handling.models import HandlingRequest


def validate_handling_request_for_duplicate(organisation_id, callsign, arrival_date, airport_id, mission_number=None,
                                            exclude_id=None):
    """
    Function check duplicate S&F Request entries for given options
    :param exclude_id:
    :param organisation_id:
    :param callsign:
    :param arrival_date:
    :param airport_id:
    :param mission_number:
    :return:
    """

    # mission_number_q = Q()
    # ON HOLD: https://aviation-data-solutions.monday.com/boards/1132439395/views/600662/pulses/1139264885
    # if mission_number:
    #     mission_number_q = Q(mission_number__iexact=mission_number)

    qs = HandlingRequest.objects.filter(
        airport_id=airport_id,
        callsign__iexact=callsign,
        movement__direction__code='ARRIVAL',
        movement__date__date=arrival_date,
        customer_organisation_id=organisation_id,
    ).exclude(pk=exclude_id)

    return qs.first()


def validate_handling_request_for_duplicate_v2(organisation_id,
                                               arrival_date,
                                               departure_date,
                                               airport_id,
                                               callsign=None,
                                               tail_number_id=None,
                                               mission_number=None,
                                               exclude_id=None):
    """
    Function check duplicate S&F Request entries for given options
    :param exclude_id:
    :param organisation_id:
    :param callsign:
    :param arrival_date:
    :param departure_date:
    :param airport_id:
    :param tail_number_id:
    :param mission_number:
    :return:
    """

    date_q = (
            # Inner duplicate
            (Q(eta_date__lte=arrival_date) & Q(etd_date__gte=departure_date)) |
            # Outer duplicate
            (Q(eta_date__gte=arrival_date) & Q(etd_date__lte=departure_date)) |
            # Is Arrival conflicts / Q(etd_date__lte=departure_date)
            (Q(eta_date__lte=arrival_date) & Q(etd_date__gte=arrival_date)) |
            # Is Departure conflicts / Q(eta_date__gte=arrival_date)
            (Q(etd_date__gte=departure_date) & Q(eta_date__lte=departure_date))
    )

    tail_number_q = Q()
    callsign_q = Q()

    if tail_number_id:
        tail_number_q = Q(tail_number_id=tail_number_id)
    else:
        callsign_q = Q(callsign=callsign)

    qs = HandlingRequest.objects.with_eta_etd_and_status_index().filter(
        ~Q(pk=exclude_id),
        ~Q(status__in=[5, ]),
        date_q,
        tail_number_q,
        callsign_q,
        customer_organisation_id=organisation_id,
    )

    return qs.first()


def get_overlap_checking_q(eta_field_name: str, eta_date: datetime, etd_field_name: str, etd_date: datetime):
    """
    Funtion return Q object with filter to find overlap with given eta and etd
    using given field names in Queryset. Initially developed for S&F Requests and Missions
    :param eta_field_name: str
    :param eta_date: date
    :param etd_field_name:
    :param etd_date:
    :return:
    """
    q = Q(
        (Q(**{eta_field_name + '__lte': eta_date}) & Q(**{f'{etd_field_name}__gte': etd_date})) |
        # Outer duplicate
        (Q(**{f'{eta_field_name}__gte': eta_date}) & Q(**{f'{etd_field_name}__lte': etd_date})) |
        # Is Arrival conflicts / Q(etd_date__lte=departure_date)
        (Q(**{f'{eta_field_name}__lte': eta_date}) & Q(**{f'{etd_field_name}__gte': eta_date})) |
        # Is Departure conflicts / Q(eta_date__gte=arrival_date)
        (Q(**{f'{etd_field_name}__gte': etd_date}) & Q(**{f'{eta_field_name}__lte': etd_date}))
    )
    return q


def get_person_active_crews(person, arrival_date, departure_date, exclude_sfr=None, exclude_mission=None):
    """
    Return S&F Requests and Missions where given person is participant of the crew for given dates
    :param person: Person object
    :param arrival_date: ETA of current crew mission
    :param departure_date: ETD of current crew mission
    :param exclude_sfr: HandlingRequest object to exclude
    :param exclude_mission: Mission object to exclude
    :return: HandlingRequests and Missions QuerySet's
    """
    overlapped_sfr = HandlingRequest.objects.with_eta_etd_and_status_index().filter(
        (Q(mission_crew__person=person) & Q(mission_crew__is_primary_contact=False)),
    ).filter(
        get_overlap_checking_q(eta_field_name='eta_date', eta_date=arrival_date,
                               etd_field_name='etd_date', etd_date=departure_date)
    ).exclude(pk=exclude_sfr.pk if exclude_sfr else None)

    from mission.models import Mission
    overlapped_missions = Mission.objects.include_details().filter(
        (Q(mission_crew_positions__person=person) & Q(mission_crew_positions__is_primary_contact=False)),
        get_overlap_checking_q(eta_field_name='start_date_val', eta_date=arrival_date,
                               etd_field_name='end_date_val', etd_date=departure_date)
    ).exclude(pk=exclude_mission.pk if exclude_mission else None)

    return overlapped_sfr, overlapped_missions
