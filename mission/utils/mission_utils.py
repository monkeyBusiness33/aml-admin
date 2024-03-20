import logging

from django.conf import settings

from mission.utils.mission_leg_automatic_services import mission_leg_cargo_service
from mission.utils.notifications_clients import mission_submitted_client_notifications
from mission.utils.notifications_staff import mission_submitted_staff_notifications, \
    mission_cancelled_staff_notifications

logger = logging.getLogger(__name__)


def mission_on_update_actions(mission):
    logger.info('Mission update actions')

    if not hasattr(mission, 'updated_by') or mission.updated_by is None:
        if settings.DEBUG:
            logger.error('S&F Request have no "updated_by" attribute')
        return

    is_mission_draft = mission.status['code'] == 2
    if 'callsign' in mission.changed_fields:
        if not is_mission_draft:
            mission.is_amended_callsign = True

    if 'aircraft_type_id' in mission.changed_fields:
        # TODO: implement
        pass

    modified_by_staff = mission.updated_by.user.is_staff

    if modified_by_staff:
        # Set assigned military team member in case if nobody assigned
        if not mission.assigned_mil_team_member:
            if mission.updated_by and mission.updated_by.is_mil_team:
                mission.assigned_mil_team_member = mission.updated_by

    if 'callsign' not in mission.changed_fields:
        mission.is_amended_callsign = False

    return mission


def mission_after_save(mission):
    mission_leg_cargo_service(mission)

    if not mission.meta_is_partial_save and mission.is_confirmed:
        logger.info('Launching SFR Bridge')
        from mission.utils.mission_sfr_bridge import mission_sfr_bridge
        mission_sfr_bridge(mission, mission.updated_by)

    if 'is_confirmed' in mission.changed_fields and mission.is_confirmed:
        logger.info('Sending Mission notifications')
        mission_submitted_staff_notifications(mission)
        mission_submitted_client_notifications(mission)

    if 'is_cancelled' in mission.changed_fields and mission.is_cancelled:
        mission_cancelled_staff_notifications(mission)

    return mission


def calculate_mission_status_flags(mission):
    from handling.models import HandlingRequest
    mission_sfr_qs = HandlingRequest.objects.with_status().filter(
        mission_turnaround__mission_leg__mission=mission,
    )

    has_sfr = mission_sfr_qs.exists()
    has_sfr_new = mission_sfr_qs.filter(is_new=True).exists()
    has_sfr_in_progress = mission_sfr_qs.filter(status=1).exists()
    has_sfr_confirmed = mission_sfr_qs.filter(status__in=[2, 8]).exists()
    has_sfr_amended = mission_sfr_qs.filter(status=6).exists()

    from mission.models import MissionStatusFlags
    status_flags, created = MissionStatusFlags.objects.update_or_create(
        mission=mission,
        defaults={
            'has_sfr': has_sfr,
            'has_sfr_new': has_sfr_new,
            'has_sfr_amended': has_sfr_amended,
            'has_sfr_in_progress': has_sfr_in_progress,
            'has_sfr_confirmed': has_sfr_confirmed,
        }
    )

    return mission
