from datetime import datetime

from django.utils.html import format_html


def generate_mission_number(handling_request):
    if handling_request.customer_organisation.pk == 100006 and not handling_request.mission_number:
        year = datetime.now().year
        sfr_qs = handling_request.customer_organisation.handling_requests.with_eta_etd_and_status_index().filter(
            eta_date__year=year,
        )
        existing_handling_requests_count = sfr_qs.count()
        mission_number = str(year) + str(existing_handling_requests_count + 1).zfill(4)
        return mission_number
    else:
        return handling_request.mission_number


def get_sfr_html_link(sfr, open_new_tab=False):
    open_new_tab_html = ''
    if open_new_tab:
        open_new_tab_html = 'target="_blank"'
    return format_html(f'<a href="{sfr.get_absolute_url()}" {open_new_tab_html}>{sfr.callsign}</a>')


def get_sfr_html_urls(sfr_list, open_new_tab=False) -> list:
    result = []
    for sfr in sfr_list:
        result.append(get_sfr_html_link(sfr, open_new_tab))
    return result
