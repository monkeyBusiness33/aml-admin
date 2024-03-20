from django.urls import reverse_lazy

from handling.utils.statuses_generators import get_fuel_booking_status_circle, get_ground_handling_status_circle
from mission.models import Mission


def mission_leg_get_calendar_event_html(mission_leg, app_mode):
    callsign = mission_leg.callsign_override if mission_leg.callsign_override else mission_leg.mission.callsign
    fuel_status = '--' if mission_leg.sfr_fuel_status_code == 0 else get_fuel_booking_status_circle(
        mission_leg.sfr_fuel_status_code)
    gh_status = '--' if mission_leg.ground_handling_status_code == 0 else get_ground_handling_status_circle(
        mission_leg.ground_handling_status_code)
    assigned_initials = mission_leg.mission.assigned_mil_team_member.initials if (
        mission_leg.mission.assigned_mil_team_member) else '--'
    background_color = Mission.STATUS_DETAILS[mission_leg.mission_status_code]['background_color']
    text_color = Mission.STATUS_DETAILS[mission_leg.mission_status_code]['text_color']
    departure_date = mission_leg.departure_datetime.strftime("%H:%M")
    departure_icao = mission_leg.departure_location.tiny_repr
    arrival_date = mission_leg.arrival_datetime.strftime("%H:%M")
    arrival_icao = mission_leg.arrival_location.tiny_repr

    mission_url = ''
    if app_mode == 'ops_portal':
        mission_url = reverse_lazy('admin:missions_details', kwargs={'pk': mission_leg.mission_id})
    elif app_mode == 'dod_portal':
        mission_url = reverse_lazy('dod:missions_details', kwargs={'pk': mission_leg.mission_id})

    html = f'<div><a class="fc-daygrid-event fc-daygrid-block-event fc-h-event fc-event mb-1" href="{mission_url}" ' \
           f'style="background-color: {background_color};">' \
           f'<div class="fc-event-main" style="color: {text_color};">{callsign}' \
           f'<span class="ms-auto float-end">{fuel_status} {gh_status} {assigned_initials}</span> <br>' \
           f'<div class="">{departure_date} {departure_icao} > {arrival_icao} {arrival_date}</div>' \
           f'</div>' \
           f'</a></div>'

    return html
