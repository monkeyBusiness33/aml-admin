

def handling_request_activity_logging(handling_request, author):
    """
    S&F Request Logging function, should be called on each save of existing Handling Request object.
    Processing of changes for fields which specified in 'activity_log_fields' variable.
    FK Fields should be processed separately to get readable value instead id.
    :param handling_request: S&F Request obj
    :param author: Person making changes
    :return: None
    """

    if handling_request.meta_is_first_save:
        handling_request.activity_log.create(
            record_slug='sfr_created',
            details=f'S&F Request Created from {handling_request.meta_creation_source}',
            author=handling_request.created_by,
        )

    if hasattr(handling_request, 'is_created'):
        return

    activity_log_fields = ['callsign', 'mission_number', 'type_id', 'assigned_mil_team_member_id',
                           'apacs_number', 'apacs_url', 'tail_number_id', 'aircraft_type_id',
                           'handling_agent_id',
                           ]

    for field_name in activity_log_fields:
        if field_name in handling_request.changed_fields:
            value_prev_raw = handling_request.get_field_diff(field_name)[0]
            value_new_raw = handling_request.get_field_diff(field_name)[1]
            value_prev = value_prev_raw
            value_new = value_new_raw
            details = None

            # Custom processing of some fields
            if field_name == 'assigned_mil_team_member_id':
                model_cls = handling_request.assigned_mil_team_member._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.fullname if obj_prev else ''
                value_new = obj_new.fullname if obj_new else ''

            if field_name == 'type_id':
                model_cls = handling_request.type._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.name if obj_prev else ''
                value_new = obj_new.name if obj_new else ''

            if field_name == 'aircraft_type_id':
                model_cls = handling_request.aircraft_type._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev if obj_prev else ''
                value_new = obj_new if obj_new else ''

            if field_name == 'tail_number_id':
                from aircraft.models import AircraftHistory
                obj_prev = AircraftHistory.objects.filter(pk=value_prev_raw).first()
                obj_new = AircraftHistory.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.registration if obj_prev else ''
                value_new = obj_new.registration if obj_new else ''

            if field_name == 'handling_agent_id':
                from organisation.models import Organisation
                obj_prev = Organisation.objects.filter(pk=value_prev_raw).first()
                obj_new = Organisation.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.full_repr if obj_prev else ''
                value_new = obj_new.full_repr if obj_new else ''

            if field_name in ['air_card_prefix_id', 'air_card_number', ]:
                # This fields should be processed separately.
                continue

            handling_request.activity_log.create(
                record_slug=f'sfr_{field_name}_amendment',
                value_name=handling_request._meta.get_field(field_name).verbose_name,  # noqa
                value_prev=value_prev or None,
                value_new=value_new or None,
                details=details,
                author=author,
            )

    if 'is_amended_callsign' in handling_request.changed_fields:
        value_prev_raw = handling_request.get_field_diff('is_amended_callsign')[0]
        value_new_raw = handling_request.get_field_diff('is_amended_callsign')[1]
        if value_prev_raw is True and value_new_raw is False:
            handling_request.activity_log.create(
                record_slug='sfr_callsign_amendment_confirmation',
                details=f'Amended Callsign {handling_request.callsign} has been confirmed',
                author=author,
            )

    if 'is_handling_confirmed' in handling_request.changed_fields:
        value_prev_raw = handling_request.get_field_diff('is_handling_confirmed')[0]
        value_new_raw = handling_request.get_field_diff('is_handling_confirmed')[1]
        if value_prev_raw is False and value_new_raw is True:
            handling_request.activity_log.create(
                record_slug='sfr_ground_handling_confirmation',
                details=f'Ground Handling has been confirmed',
                author=author,
            )

    if 'is_aog' in handling_request.changed_fields:
        value_prev_raw = handling_request.get_field_diff('is_aog')[0]
        value_new_raw = handling_request.get_field_diff('is_aog')[1]
        if value_prev_raw is False and value_new_raw is True:
            handling_request.activity_log.create(
                record_slug='sfr_is_aog',
                details=f'AOG: Aircraft On Ground, S&F Request processing paused',
                author=author,
            )
        elif value_prev_raw is True and value_new_raw is False:
            handling_request.activity_log.create(
                record_slug='sfr_is_not_aog',
                details=f'AOG: Aircraft Serviceable, S&F Request processing resumed',
                author=author,
            )

    if 'is_awaiting_departure_update_confirmation' in handling_request.changed_fields:
        value_prev_raw = handling_request.get_field_diff('is_awaiting_departure_update_confirmation')[0]
        value_new_raw = handling_request.get_field_diff('is_awaiting_departure_update_confirmation')[1]
        if value_prev_raw is True and value_new_raw is False:
            handling_request.activity_log.create(
                record_slug='sfr_ground_handling_departure_update_confirmation',
                details=f'Departure Update has been confirmed',
                author=author,
            )

    # Processing of related fields pairs
    if 'air_card_prefix_id' in handling_request.changed_fields or 'air_card_number' in handling_request.changed_fields:
        prefix_cls = handling_request.air_card_prefix._meta.model  # noqa
        prefix_prev_diff = handling_request.get_field_diff('air_card_prefix_id')
        prefix_new_diff = handling_request.get_field_diff('air_card_prefix_id')
        prefix_prev_raw = prefix_prev_diff[0] if prefix_prev_diff else getattr(
            handling_request.air_card_prefix, 'pk', None)
        prefix_new_raw = prefix_new_diff[1] if prefix_new_diff else getattr(
            handling_request.air_card_prefix, 'pk', None)

        number_prev_diff = handling_request.get_field_diff('air_card_number')
        number_new_diff = handling_request.get_field_diff('air_card_number')
        number_prev_raw = number_prev_diff[0] if number_prev_diff else handling_request.air_card_number
        number_new_raw = number_new_diff[1] if number_new_diff else handling_request.air_card_number

        prefix_prev = prefix_cls.objects.filter(pk=prefix_prev_raw).first()
        prefix_new = prefix_cls.objects.filter(pk=prefix_new_raw).first() or None
        prefix_prev = prefix_prev.number_prefix if prefix_prev else ''
        prefix_new = prefix_new.number_prefix if prefix_new else ''

        value_prev = f'{prefix_prev}{number_prev_raw}'
        value_new = f'{prefix_new}{number_new_raw}'
        handling_request.activity_log.create(
            record_slug=f'sfr_aircard_number_amendment',
            value_name=handling_request._meta.get_field('air_card_number').verbose_name,  # noqa
            value_prev=value_prev,
            value_new=value_new,
            author=author,
        )

    if {'fuel_required_id', 'fuel_quantity', 'fuel_unit_id'}.intersection(handling_request.changed_fields):
        if not handling_request.fuel_required:
            fuel_amendment_message = f'Fuel Amended - {handling_request.fuel_required_full_repr}'
        else:
            fuel_amendment_message = f'Fuel Amended - {handling_request.fuel_required_full_repr}'

        handling_request.activity_log.create(
            author=handling_request.updated_by,
            record_slug='sfr_fuel_amendment',
            details=fuel_amendment_message,
        )

    if 'parking_apron' in handling_request.changed_fields or 'parking_stand' in handling_request.changed_fields:
        diff_apron = handling_request.get_field_diff('parking_apron')
        diff_stand = handling_request.get_field_diff('parking_stand')
        parking_apron_prev_raw = diff_apron[0] if diff_apron else ''
        parking_stand_prev_raw = diff_stand[0] if diff_stand else ''
        parking_apron_new_raw = diff_apron[1] if diff_apron else ''
        parking_stand_new_raw = diff_stand[1] if diff_stand else ''

        handling_request.activity_log.create(
            record_slug=f'sfr_parking_confirmation',
            details=get_parking_confirmation_message_text(parking_apron_prev_raw, parking_stand_prev_raw,
                                                          parking_apron_new_raw, parking_stand_new_raw),
            author=author,
        )

    return handling_request


def movement_activity_logging(movement, author):
    """
    S&F Request Movement Activity Logging function, should be called on each save of existing Movement object.
    Process changes for fields which specified in 'activity_log_fields' variable.
    FK Fields should be processed separately to get readable value instead id.
    :param movement: HandlingRequestMovement obj
    :param author: Person making changes
    :return: None
    """
    activity_log_fields = [
        'date', 'airport_id', 'crew', 'ppr_number',
    ]

    for field_name in activity_log_fields:
        if field_name in movement.changed_fields:
            value_prev_raw = movement.get_field_diff(field_name)[0]
            value_new_raw = movement.get_field_diff(field_name)[1]
            value_prev = value_prev_raw
            value_new = value_new_raw

            # Custom processing of some fields
            if field_name == 'airport_id':
                from organisation.models import Organisation
                obj_prev = Organisation.objects.filter(pk=value_prev_raw).first()
                obj_new = Organisation.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.tiny_repr if obj_prev else ''
                value_new = obj_new.tiny_repr if obj_new else ''

            if field_name == 'date':
                value_prev = value_prev_raw.strftime("%Y-%m-%d %H:%M") if value_prev_raw else ''
                value_new = value_new_raw.strftime("%Y-%m-%d %H:%M") if value_new_raw else ''

            movement.activity_log.create(
                record_slug=f'sfr_movement_{field_name}_amendment',
                value_name=movement._meta.get_field(field_name).verbose_name,  # noqa
                value_prev=value_prev,
                value_new=value_new,
                author=author,
            )

    if {'is_passengers_onboard', 'is_passengers_tbc', 'passengers'}.intersection(movement.changed_fields):
        movement.activity_log.create(
            record_slug=f'sfr_movement_passengers_amendment',
            author=author,
            details=f'passengers updated to "{movement.passengers_full_repr}"'
        )


def get_parking_confirmation_message_text(old_parking_apron, old_parking_stand, new_parking_apron, new_parking_stand):
    if not old_parking_apron and not old_parking_stand:
        return f'Parking has been confirmed (Apron: "{new_parking_apron}", Stand: "{new_parking_stand}")'
    else:
        return f'Parking updated from (Apron: "{old_parking_apron}", Stand: "{old_parking_stand}") ' \
               f'to (Apron: "{new_parking_apron}", Stand: "{new_parking_stand}")'
