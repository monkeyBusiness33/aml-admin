

def mission_activity_logging(mission, author):
    """
    Mission Activity Logging function, should be called on each save of existing Mission object.
    Process changes for fields which specified in 'activity_log_fields' variable.
    FK Fields should be processed separately to get readable value instead id.
    :param mission: Mission obj
    :param author: Person making changes
    :return: None
    """

    if mission.meta_is_first_save:
        mission.activity_log.create(
            record_slug=f'mission_created',
            details='Mission Created',
            author=mission.updated_by,
        )

    if hasattr(mission, 'is_created'):
        return

    activity_log_fields = ['assigned_mil_team_member_id', 'aircraft_id', 'type_id', 'callsign',
                           'aircraft_type_id', 'apacs_number', 'apacs_url', 'air_card_prefix_id', 'air_card_number',
                           ]

    for field_name in activity_log_fields:
        if field_name in mission.changed_fields:
            value_prev_raw = mission.get_field_diff(field_name)[0]
            value_new_raw = mission.get_field_diff(field_name)[1]
            value_prev = value_prev_raw
            value_new = value_new_raw

            # Custom processing of some fields
            if field_name == 'assigned_mil_team_member_id':
                from user.models import Person
                person_prev = Person.objects.filter(pk=value_prev_raw).first()
                person_new = Person.objects.filter(pk=value_new_raw).first()
                value_prev = person_prev.fullname if person_prev else ''
                value_new = person_new.fullname if person_new else ''

            if field_name == 'aircraft_id':
                model_cls = mission.aircraft._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.registration if obj_prev else ''
                value_new = obj_new.registration if obj_new else ''

            if field_name == 'type_id':
                model_cls = mission.type._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.name if obj_prev else ''
                value_new = obj_new.name if obj_new else ''

            if field_name == 'aircraft_type_id':
                model_cls = mission.aircraft_type._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev if obj_prev else ''
                value_new = obj_new if obj_new else ''

            if field_name in ['air_card_prefix_id', 'air_card_number', ]:
                # This fields should be processed separately.
                continue

            mission.activity_log.create(
                record_slug=f'mission_{field_name}_amendment',
                value_name=mission._meta.get_field(field_name).verbose_name,  # noqa
                value_prev=value_prev,
                value_new=value_new,
                author=author,
            )

    # Processing of related fields pairs
    if 'air_card_prefix_id' in mission.changed_fields or 'air_card_number' in mission.changed_fields:
        prefix_cls = mission.air_card_prefix._meta.model  # noqa
        prefix_prev_diff = mission.get_field_diff('air_card_prefix_id')
        prefix_new_diff = mission.get_field_diff('air_card_prefix_id')
        prefix_prev_raw = prefix_prev_diff[0] if prefix_prev_diff else getattr(mission.air_card_prefix, 'pk',
                                                                               None)
        prefix_new_raw = prefix_new_diff[1] if prefix_new_diff else getattr(mission.air_card_prefix, 'pk', None)
        number_prev_diff = mission.get_field_diff('air_card_number')
        number_new_diff = mission.get_field_diff('air_card_number')
        number_prev_raw = number_prev_diff[0] if number_prev_diff else mission.air_card_number
        number_new_raw = number_new_diff[1] if number_new_diff else mission.air_card_number

        prefix_prev = prefix_cls.objects.filter(pk=prefix_prev_raw).first()
        prefix_new = prefix_cls.objects.filter(pk=prefix_new_raw).first() or None
        prefix_prev = prefix_prev.number_prefix if prefix_prev else ''
        prefix_new = prefix_new.number_prefix if prefix_new else ''

        value_prev = f'{prefix_prev}{number_prev_raw}'
        value_new = f'{prefix_new}{number_new_raw}'
        mission.activity_log.create(
            record_slug=f'mission_aircard_number_amendment',
            value_name=mission._meta.get_field('air_card_number').verbose_name,  # noqa
            value_prev=value_prev,
            value_new=value_new,
            author=author,
        )

    if 'is_amended_callsign' in mission.changed_fields:
        value_prev_raw = mission.get_field_diff('is_amended_callsign')[0]
        value_new_raw = mission.get_field_diff('is_amended_callsign')[1]
        if value_prev_raw is True and value_new_raw is False:
            mission.activity_log.create(
                record_slug='mission_callsign_amendment_confirmation',
                details=f'Amended Callsign {mission.callsign} has been confirmed',
                author=author,
            )

    if 'is_confirmed' in mission.changed_fields:
        value_prev_raw = mission.get_field_diff('is_confirmed')[0]
        value_new_raw = mission.get_field_diff('is_confirmed')[1]
        if not value_prev_raw and value_new_raw is True:
            mission.activity_log.create(
                record_slug='mission_confirmation',
                details=f'Mission has been confirmed',
                author=author,
            )

    if 'is_cancelled' in mission.changed_fields:
        value_prev_raw = mission.get_field_diff('is_cancelled')[0]
        value_new_raw = mission.get_field_diff('is_cancelled')[1]
        if not value_prev_raw and value_new_raw is True:
            mission.activity_log.create(
                record_slug='mission_cancelled',
                details=f'Mission has been cancelled',
                author=author,
            )

    if 'mission_number_prefix' in mission.changed_fields or 'mission_number' in mission.changed_fields:
        field_name = 'mission_number'
        mission_number_prefix_diff = mission.get_field_diff('mission_number_prefix')
        mission_number_prefix_prev = mission_number_prefix_diff[0] if mission_number_prefix_diff else getattr(
            mission, 'mission_number_prefix', '')
        mission_number_prefix_new = mission_number_prefix_diff[1] if mission_number_prefix_diff else getattr(
            mission, 'mission_number_prefix', '')
        mission_number_diff = mission.get_field_diff('mission_number')
        mission_number_prev = mission_number_diff[0] if mission_number_diff else getattr(mission, 'mission_number', '')
        mission_number_new = mission_number_diff[1] if mission_number_diff else getattr(mission, 'mission_number', '')

        value_prev = f'{mission_number_prefix_prev}{mission_number_prev}'
        value_new = f'{mission_number_prefix_new}{mission_number_new}'

        mission.activity_log.create(
            record_slug=f'mission_{field_name}_amendment',
            value_name=mission._meta.get_field(field_name).verbose_name,  # noqa
            value_prev=value_prev,
            value_new=value_new,
            author=author,
        )


def mission_leg_activity_logging(mission_leg):
    """
    MissionLeg Activity Logging function, should be called on each save of existing MissionLeg object.
    Process changes for fields which specified in 'activity_log_fields' variable.
    FK Fields should be processed separately to get readable value instead id.
    :param mission_leg: MissionLeg obj
    :return: None
    """

    if not hasattr(mission_leg.mission, 'is_created') and mission_leg.meta_is_first_save:
        mission_leg.activity_log.create(
            record_slug=f'mission_leg_created',
            details='Added to the Mission',
            author=mission_leg.updated_by,
        )

    # Stop working on continuous savings for newly created Flight Leg
    if hasattr(mission_leg, 'is_created'):
        return

    activity_log_fields = [
        'callsign_override',
        'departure_location_id', 'departure_datetime', 'departure_diplomatic_clearance',
        'arrival_location_id', 'arrival_datetime', 'arrival_diplomatic_clearance',
        'aircraft_type_override_id', 'aircraft_override_id',
        'pob_crew', 'pob_pax', 'cob_lbs',
    ]

    for field_name in activity_log_fields:
        if field_name in mission_leg.changed_fields:
            value_prev_raw = mission_leg.get_field_diff(field_name)[0]
            value_new_raw = mission_leg.get_field_diff(field_name)[1]
            value_prev = value_prev_raw
            value_new = value_new_raw

            # Custom processing of some fields
            if field_name in ['departure_location_id', 'arrival_location_id']:
                model_cls = mission_leg.departure_location._meta.model  # noqa
                obj_prev = model_cls.objects.filter(pk=value_prev_raw).first()
                obj_new = model_cls.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.tiny_repr if obj_prev else ''
                value_new = obj_new.tiny_repr if obj_new else ''

            if field_name == 'aircraft_type_override_id':
                from aircraft.models import AircraftType
                obj_prev = AircraftType.objects.filter(pk=value_prev_raw).first()
                obj_new = AircraftType.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev if obj_prev else ''
                value_new = obj_new if obj_new else ''

            if field_name == 'aircraft_override_id':
                from aircraft.models import AircraftHistory
                obj_prev = AircraftHistory.objects.filter(pk=value_prev_raw).first()
                obj_new = AircraftHistory.objects.filter(pk=value_new_raw).first()
                value_prev = obj_prev.registration if obj_prev else ''
                value_new = obj_new.registration if obj_new else ''

            if field_name in ['departure_datetime', 'arrival_datetime']:
                value_prev = value_prev_raw.strftime("%Y-%m-%d %H:%M") if value_prev_raw else ''
                value_new = value_new_raw.strftime("%Y-%m-%d %H:%M") if value_new_raw else ''

            if field_name in ['air_card_prefix_id', 'air_card_number', ]:
                # This fields should be processed separately.
                continue

            mission_leg.activity_log.create(
                record_slug=f'mission_leg_{field_name}_amendment',
                value_name=mission_leg._meta.get_field(field_name).verbose_name,  # noqa
                value_prev=value_prev,
                value_new=value_new,
                author=mission_leg.updated_by,
            )

    if 'arrival_aml_service' in mission_leg.changed_fields:
        value_prev_raw = mission_leg.get_field_diff('arrival_aml_service')[0]
        value_new_raw = mission_leg.get_field_diff('arrival_aml_service')[1]
        if not value_prev_raw and value_new_raw is True:
            mission_leg.activity_log.create(
                record_slug='mission_leg_turnaround_enabled',
                details=f'AML Servicing enabled',
                author=mission_leg.updated_by,
            )
        if value_prev_raw and value_new_raw is False:
            mission_leg.activity_log.create(
                record_slug='mission_leg_turnaround_disabled',
                details=f'AML Servicing disabled',
                author=mission_leg.updated_by,
            )
