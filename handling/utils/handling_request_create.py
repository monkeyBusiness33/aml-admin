import copy


def create_recurrence_handling_request(original_handling_request, arrival_date, departure_date):
    recurrence_request = copy.deepcopy(original_handling_request)
    recurrence_request.pk = None
    recurrence_request.skip_signal = True
    recurrence_request.save()

    for crew_member in original_handling_request.mission_crew.all():
        crew_member.pk = None
        crew_member.handling_request = recurrence_request
        crew_member.save()

    delattr(recurrence_request, 'skip_signal')

    recurrence_arrival_movement = copy.deepcopy(original_handling_request.arrival_movement)
    recurrence_arrival_movement.pk = None
    recurrence_arrival_movement.request = recurrence_request
    recurrence_arrival_movement.date = arrival_date
    recurrence_arrival_movement.save()

    recurrence_departure_movement = copy.deepcopy(original_handling_request.departure_movement)
    recurrence_departure_movement.pk = None
    recurrence_departure_movement.request = recurrence_request
    recurrence_departure_movement.date = departure_date
    recurrence_departure_movement.save()

    return recurrence_request
