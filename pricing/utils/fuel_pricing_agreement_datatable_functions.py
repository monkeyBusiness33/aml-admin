from itertools import groupby
from django.urls import reverse_lazy
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_badge


def get_datatable_ipa_tooltip_html(ipas: list):
    return 'IPA at location: ' + \
        (f'<ul><li>' + '</li><li>'.join(ipas) + '</li></ul>' if ipas else '--')


def get_datatable_agreement_locations_list(agreement: 'FuelAgreement'):
    '''
    Function takes FuelAgreement and returns badges string with airport
    icao and iata codes, and tooltips indicating IPA(s) at each location
    '''
    location_groups = groupby(
        agreement.all_pricing_locations,
        lambda x: x[0]
    )
    location_dict = {k: [ipa for (loc, ipa) in list(v) if ipa is not None] for k, v in location_groups}
    badge_str = ''

    for location, ipas in sorted(location_dict.items()):
        badge_str += get_datatable_badge(
            badge_text=location,
            badge_class='bg-info datatable-badge-normal badge-multiline badge-250',
            tooltip_text=get_datatable_ipa_tooltip_html(location_dict[location]),
            tooltip_enable_html=True
        )

    return f'<div class="d-flex flex-wrap">{badge_str}</div>'


def get_datatable_fees_action_btns(btn_params, request):
    view_btn = get_datatable_actions_button(
        button_text='',
        button_url=btn_params['view_url'],
        button_class='fa-eye',
        button_popup='View Details',
        button_active=request.user.has_perm(btn_params['view_perm']),
        button_modal=False,
        modal_validation=True)

    edit_btn = get_datatable_actions_button(
        button_text='',
        button_url=btn_params['edit_url'],
        button_class='fa-edit',
        button_popup='Edit',
        button_active=request.user.has_perm(btn_params['edit_perm']))

    supersede_btn = get_datatable_actions_button(
        button_text='',
        button_url=btn_params['supersede_url'],
        button_class='fa-reply',
        button_popup='Supersede',
        button_active=request.user.has_perm(btn_params['supersede_perm'])
    ) if 'supersede_url' in btn_params else ''

    archive_btn = get_datatable_actions_button(
        button_text='',
        button_url=btn_params['archive_url'],
        button_class='fa-trash text-danger',
        button_popup='Archive',
        button_active=request.user.has_perm(btn_params['archive_perm']),
        button_modal=True,
        modal_validation=False)

    return view_btn + edit_btn + supersede_btn + archive_btn
