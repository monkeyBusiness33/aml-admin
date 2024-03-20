from tempfile import NamedTemporaryFile

import tablib
from django.db.models import Q


def export_handling_requests_data(qs, start_date, end_date, only_upcoming=False):

    only_upcoming_q = Q()
    if only_upcoming:
        only_upcoming_q = ~Q(status__in=[4, 5, 7])

    qs = qs.with_eta_etd_and_status_index().filter(
        only_upcoming_q,
        eta_date__date__gte=start_date,
        eta_date__date__lte=end_date,
    )

    if not qs.exists():
        return None

    data_list = []
    data = tablib.Dataset()
    for handling_request in qs:
        data_list.append({
            'callsign': handling_request.callsign,
            'tail_number': handling_request.tail_number or '',
            'location': handling_request.airport.tiny_repr,
            'arrival_date': handling_request.arrival_movement.date_capitalized if
            handling_request.arrival_movement else '',
            'departure_date': handling_request.departure_movement.date_capitalized if
            handling_request.departure_movement else '',
            'mission_number': handling_request.mission_number or '',
            'primary_mission_contact': handling_request.primary_contact.fullname if
            handling_request.primary_contact else '',
        })

    data.headers = data_list[0].keys()
    data.extend([item.values() for item in data_list])

    csv_data = data.export('csv')

    fh = NamedTemporaryFile()
    fh.write(bytes(csv_data, 'UTF-8'))
    fh.seek(0)

    return fh
