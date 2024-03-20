def update_or_create_sfr(author,
                         handling_request=None,
                         handling_request_data=None,
                         arrival_movement_data=None,
                         departure_movement_data=None,
                         ):
    """
    This function is designed as core, shared function to handle S&F Request or it's parts updating
    to prevent code duplication across entire app
    :param author:
    :param handling_request:
    :param handling_request_data:
    :param arrival_movement_data:
    :param departure_movement_data:
    :return:
    """
    from handling.models import HandlingRequest, HandlingRequestMovement
    from handling.utils.email_diff_generator import generate_diff_dict

    handling_request_created = False
    if handling_request_data is None:
        handling_request_data = {}

    # Create new S&F Request
    if not handling_request:
        handling_request = HandlingRequest(created_by=author)
        handling_request_created = True
        handling_request.skip_signal = True

    # Create diff dict for amendment notifications
    old_instance_diff = None
    if not handling_request_created:
        old_instance_diff = generate_diff_dict(handling_request=handling_request)
        handling_request.updated_by = author

    if handling_request_data:
        for key, value in handling_request_data.items():
            setattr(handling_request, key, value)

        handling_request.save()
        if hasattr(handling_request, 'skip_signal'):
            delattr(handling_request, 'skip_signal')

    # Create or update Arrival Movement
    if arrival_movement_data:
        arrival_movement = handling_request.arrival_movement or HandlingRequestMovement(direction_id='ARRIVAL')
        arrival_movement.request = handling_request
        arrival_movement.updated_by = author
        for key, value in arrival_movement_data.items():
            setattr(arrival_movement, key, value)
        arrival_movement.movement_meta_prevent_sfr_save = True
        arrival_movement.save()

        if arrival_movement.amendment_fields.intersection(arrival_movement.changed_fields):
            handling_request.is_movement_amended = True

    # Create or update Departure Movement
    if departure_movement_data:
        departure_movement = handling_request.departure_movement or HandlingRequestMovement(direction_id='DEPARTURE')
        departure_movement.request = handling_request
        departure_movement.updated_by = author
        for key, value in departure_movement_data.items():
            setattr(departure_movement, key, value)
        departure_movement.movement_meta_prevent_sfr_save = True
        departure_movement.save()

        if departure_movement.amendment_fields.intersection(departure_movement.changed_fields):
            handling_request.is_movement_amended = True

    # Finalize S&F Request
    handling_request.old_instance_diff = old_instance_diff
    handling_request.save()
    if handling_request_created:
        # Trigger post_save signal to create/update fuel order
        from django.db.models.signals import post_save
        post_save.send(HandlingRequest, instance=handling_request, created=handling_request.created)

    return handling_request
