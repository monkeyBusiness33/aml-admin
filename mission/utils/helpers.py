from django.utils.html import format_html


def get_mission_html_link(mission, open_new_tab=False):
    open_new_tab_html = ''
    if open_new_tab:
        open_new_tab_html = ' target="_blank"'
    return format_html(
        f'<a href="{mission.get_absolute_url()}"{open_new_tab_html}>{mission.mission_number} / {mission.callsign}</a>'
    )


def get_mission_html_urls(missions_list, open_new_tab=False):
    result = []
    for mission in missions_list:
        result.append(get_mission_html_link(mission, open_new_tab))
    return result
