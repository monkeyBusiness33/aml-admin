from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, DateField, Case, When, OuterRef, Exists


def get_datatable_organisation_status_badge(operational_status):
    '''
    Function returns organisation status badge for datatable
    '''
    if operational_status['code'] in ['sanctioned', 'ceased_trading']:
        return f'<span class="badge datatable-organisation-status-badge me-1 {operational_status["badge_bg"]}" data-search="{operational_status["code"]}"> \
                {operational_status["text"]}</span>'


def get_datatable_missing_details_status_badge(data_status):
    '''
    Function returns missing details status badge for datatable
    This is to check if organisation is missing details needed for its
    primary type and indicate that to users
    '''
    if data_status['missing_details']:
        return f'<span class="badge datatable-organisation-status-badge me-1 {data_status["badge_bg"]}" data-search="{data_status["text"]}"> \
                {data_status["text"]}</span>'


def get_datatable_oilco_fuel_badges(fuel_types):
    '''
    Funciton require ipa locations object on input
    Returns badges string with the IPA location fuel types
    '''
    badges_list = []
    fuel_types_list = fuel_types.values_list('name', flat=True).distinct()
    for fuel_type in fuel_types_list:
        tag_html = f'<span class="badge bg-gray-600 p-1 me-1" data-bs-toggle="tooltip" \
            data-bs-placement="top" title="{fuel_type}" >{fuel_type}</span>'
        badges_list.append(tag_html)

    return ' '.join(map(str, badges_list))


def get_datatable_dao_countries_badges(dao):
    '''
    Function require dao object on input
    Returns badges string with the DAO responsible countries
    '''
    badges_list = []
    countries_list = dao.dao_countries.all().values_list('name', flat=True)

    for country_name in countries_list:
        tag_html = f'<span class="badge bg-gray-600 datatable-badge-normal me-1" data-bs-toggle="tooltip" data-bs-placement="top" title="{country_name}" >{country_name}</span>'
        badges_list.append(tag_html)
    return ''.join(map(str, badges_list))


def get_datatable_service_provided_services(service_provider_location):
    '''
    Function require OrganisationServiceProviderLocation object on input
    Returns badges string with the location services
    '''
    badges_list = []
    services_list = service_provider_location.ground_services.values_list(
        'name', flat=True)

    for service in services_list:
        tag_html = f'<span class="badge bg-gray-600 datatable-badge-normal badge-multiline badge-250 me-1 m-1" data-bs-toggle="tooltip" \
            data-bs-placement="top" title="{service}" >{service}</span>'
        badges_list.append(tag_html)
    return ''.join(map(str, badges_list))


def get_datatable_badge(badge_text: str,
                        badge_class: str = 'bg-gray-300',
                        background_color: str = '',
                        text_color: str = '',
                        tooltip_text: str = None,
                        tooltip_placement: str = 'top',
                        tooltip_enable_html=False):
    """
    Return Bootstrap badge with given text and class or given colors
    """
    tooltip_html = ''
    if tooltip_text:
        tooltip_html = f'data-bs-toggle="tooltip" data-bs-placement="{tooltip_placement}" title="{tooltip_text}"' \
                       f'data-bs-html="{"true" if tooltip_enable_html else "false"}"'

    style = ''
    if background_color:
        style += f'background-color: {background_color};'
    if text_color:
        style += f'color: {text_color};'

    return f'<span class="badge {badge_class} m-1" style="{style}" {tooltip_html}>{badge_text}</span>'


def get_datatable_badge_from_status(status: dict, badge_class: str = ''):
    """
    Return Bootstrap badge based on status
    """
    badge_text = status.get('detail', '')
    text_color = status.get('text_color', '')
    background_color = status.get('background_color', '')
    style_html=f'style="{f"color: {text_color};" if text_color else ""}' \
               f'{f"background-color: {background_color};" if background_color else ""}"'


    return f'<span class="badge {badge_class}" {style_html} m-1">{badge_text}</span>'


def get_fontawesome_icon(icon_name: str, tooltip_text: str = None, tooltip_placement: str = 'top',
                         hidden_value: str = '', fontawesome_family_class: str = 'fas', additional_classes: str = '',
                         tooltip_enable_html=False, margin_class='ms-1'):
    tooltip_html = ''
    if tooltip_text:
        tooltip_html = f'data-bs-toggle="tooltip" data-bs-placement="{tooltip_placement}" title="{tooltip_text}" ' \
                       f'data-bs-html="{"true" if tooltip_enable_html else "false"}"'

    return (f'<i class="{fontawesome_family_class} fa-{icon_name} {margin_class} {additional_classes}"'
            f' data-hidden-value="{hidden_value}" {tooltip_html}></i>')


def get_colored_circle(color: str, text: str = '', tooltip_text: str = '', tooltip_placement: str = 'top',
                       additional_classes: str = ''):
    tooltip_html = ''
    if tooltip_text:
        tooltip_html = f'data-bs-toggle="tooltip" data-bs-placement="{tooltip_placement}" title="{tooltip_text}"'

    html = f'<span class="circle status-circle-{color} {additional_classes}" {tooltip_html}>{text or ""}</span>'

    return html


def get_datatable_trip_support_company_clients(organisation):
    '''
    Function require Organisation object on input
    Returns badges string with the trip support clients
    '''
    badges_list = []
    clients_list = organisation.trip_support_clients.values_list(
        'details__registered_name', flat=True)

    for client in clients_list:
        tag_html = f'<span class="badge bg-gray-600 datatable-badge-normal badge-multiline badge-250 me-1 m-1" data-bs-toggle="tooltip" \
            data-bs-placement="top" title="{client}" >{client}</span>'
        badges_list.append(tag_html)
    return ''.join(map(str, badges_list))


def get_datatable_person_positions(qs):
    '''
    Function require organisation_people(history) QS on input
    Returns badges string with the Person positions
    '''
    badges_list = []
    positions = qs.values(
    'job_title',
    registered_name=F('organisation__details__registered_name'),
    trading_name=F('organisation__details__trading_name'),
    )

    for position in positions:
        if position['trading_name'] not in ('', None):
            organisation_name =  f"{position['registered_name']} T/A {position['trading_name']}"
        else:
            organisation_name = position['registered_name']

        badge_text = f"{position['job_title']} at {organisation_name}"

        tag_html = f'<span class="badge bg-gray-600 datatable-badge-normal badge-multiline badge-250 me-1 m-1" data-bs-toggle="tooltip" \
            data-bs-placement="top" title="{badge_text}" >{badge_text}</span>'
        badges_list.append(tag_html)

    return ''.join(map(str, badges_list))


def get_datatable_actions_button(button_text: str,
                                 button_url: str,
                                 button_active: bool,
                                 button_class: str = None,
                                 button_icon: str = None,
                                 button_popup: str = None,
                                 button_modal: bool = False,
                                 modal_validation: bool = True,
                                 button_modal_size: str = None):
    '''
    Function returns html contains button using desired options
    '''
    if not button_active:
        button_state = 'disabled'
    else:
        button_state = ''
    if not button_class:
        button_class = 'btn-secondary'

    if modal_validation:
        modal_validation_class = 'modal_button_validation'
    else:
        modal_validation_class = 'modal_button_novalidation'

    if button_modal_size:
        modal_size_attribute = 'data-modal="' + button_modal_size  + '"'
    else:
        modal_size_attribute = ''

    if button_modal:
        if button_text == '':
            return f'<button class="{modal_validation_class} bs-modal btn p-0 text-primary fw-bolder fas {button_class}" \
                data-bs-toggle="tooltip" data-bs-placement="top" {modal_size_attribute} title="{button_popup or ""}" \
                type="button" name="button" \
                data-form-url="{button_url}" {button_state}>{button_text}</button>'
        if button_text != '':
            return f'<button class="{modal_validation_class} bs-modal btn btn-sm compact_datatable_btn {button_class}" \
                            data-bs-toggle="tooltip" data-bs-placement="top" title="{button_popup or ""}" ' \
                            f'type="button" name="button" \
                            data-form-url="{button_url}" {button_state}>' \
                            f'<i class="fas {button_icon or ""}"></i>' \
                            f'{button_text}</button>'
    else:
        # Button with icon, with the same formatting as the modal buttons
        if button_icon:
            return f'<a class="bs-modal btn btn-sm compact_datatable_btn {button_class} {button_state}" \
                    data-bs-toggle="tooltip" data-bs-placement="top" title="{button_popup or ""}" type="button" name="button" \
                    href="{button_url}">' \
                    f'<i class="fas {button_icon or ""}"></i>{button_text}</a>'
        else:
            return f'<a class="btn p-0 text-primary fw-bolder fas {button_class} {button_state}" \
                    data-bs-toggle="tooltip" data-bs-placement="top" title="{button_popup or ""}" type="button" name="button" \
                    href="{button_url}">{button_text}</a>'


def get_datatable_clipped_value(text: str, max_length: int, url: str = None):
    """
    Return clipped value with added popup which displays full text, optionally could be returned as link
    :param text: Input value
    :param max_length: Number of chars to keep visible
    :param url: Optional make value a linked to URL
    :return: String with html
    """
    is_clipped = False
    long_text = text
    tooltip_html = ''

    if not text:
        return ''

    if len(text) <= max_length:
        short_text = text
    else:
        short_text = text[:max_length]
        short_text += '&hellip;'
        is_clipped = True

    if is_clipped:
        tooltip_html = f'data-bs-toggle="tooltip" data-bs-placement="top" title="{long_text}"'

    if url:
        html = f'<a class="link-icon" href="{url}" {tooltip_html}>{short_text}</a>'
    else:
        html = f'<span {tooltip_html}>{short_text}</span>'

    return html


def store_datatable_ordering(view, params):
    # Store latest ordering in a session variable
    ordering_key = view.__class__.__name__.lower() + '_datatable_ordering'
    ordering = [str(o).lower().split(': ') for o in params['orders']]
    view.request.session[ordering_key] = ordering


def get_datatable_ordering(view, default):
    # Get ordering from session variable
    ordering_key = view.__class__.__name__.lower() + '_datatable_ordering'

    return view.request.session.get(ordering_key, default)


def get_datatable_text_with_tooltip(text: str,
                                    span_class: str = '',
                                    tooltip_text: str = None,
                                    tooltip_placement: str = 'top',
                                    tooltip_enable_html=False):
    """
    Return text span with a tooltip
    """
    tooltip_html = ''
    if tooltip_text:
        tooltip_html = f'data-bs-toggle="tooltip" data-bs-placement="{tooltip_placement}" title="{tooltip_text}"' \
                       f'data-bs-html="{"true" if tooltip_enable_html else "false"}"'

    return f'<span class="{span_class}" {tooltip_html}>{text}</span>'
