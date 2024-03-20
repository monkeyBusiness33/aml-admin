from celery import shared_task

from core.tasks import send_push


@shared_task
def mission_submitted_client_notifications(mission):
    """
    Send client notifications after Mission saving
    :param mission: Mission
    :return:
    """
    if not hasattr(mission.requesting_person, 'user'):
        return

    send_push.delay(
        title='{mission_number} - {callsign} - {start_date} / {end_date}'.format(
            mission_number=mission.mission_number_repr,
            callsign=mission.callsign,
            start_date=mission.start_date.strftime("%b-%d-%Y"),
            end_date=mission.end_date.strftime("%b-%d-%Y"),
        ),
        body='Mission {mission_number} has been received by the AML team and is being processed.'.format(
            mission_number=mission.mission_number_repr,
        ),
        data={
            'mission_id': str(mission.pk),
        },
        users=[mission.requesting_person.user.pk, ]
    )
