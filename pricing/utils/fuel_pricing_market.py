from core.utils.datatables_functions import get_datatable_actions_button
from django.urls import reverse_lazy
from decimal import Decimal

def get_datatable_pld_status_with_formatting(status):
    '''
    Function require PLD status
    returns appropriately formatted HTML that can be displayed on the PLD page
    '''
    tag_html = f'<span class="badge datatable-badge-normal pld_{status.replace(" ","_").lower()} m-1">{status}</span>'

    return tag_html

def get_datatable_airport_location(pld_id):
    '''
    Function require FuelPricingMarketPldLocation id on input
    Returns badges string with airport icao and iata codes and associated status
    '''
    badges_list = ['<div class="badges-wrapper">']

    from ..models import FuelPricingMarketPldLocation
    location_and_status = FuelPricingMarketPldLocation.objects.filter(pld_id = pld_id).with_status().with_details()\
                                                   .values_list('icao_iata', 'location_status')

    for entry in location_and_status:
        location = entry[0]
        status = entry[1].lower().replace(" ", "_")
        tag_html = f'<span class="badge pld_location location_{status} datatable-badge-normal badge-multiline badge-250 me-1 m-1">\
                    {location}</span>'
        badges_list.append(tag_html)
    badges_list.append('</div>')
    return ''.join(map(str, badges_list))


def get_datatable_pld_button_logic(self, row, obj):
    '''
    Function extends the customize_row function in the datatable
    Returns appropriate buttons based on conditions
    '''
    # Always displayed
    update_btn =  get_datatable_actions_button(button_text='Update',
                                                     button_url=reverse_lazy(
                                                    'admin:fuel_pricing_market_document_details',
                                                    kwargs={'pk': obj.pk}),
                                                    button_class='btn-outline-primary pld_update',
                                                    button_icon='fa-edit',
                                                    button_active=self.request.user.has_perm(
                                                    'pricing.p_view'),
                                                    button_modal=False)

    # Allow supersede only if the PLD in question is the most recent one
    # No use currently, we always display is_current PLDs
    if obj.is_current:
        button_active_attr = self.request.user.has_perm('pricing.p_create')
    else:
        button_active_attr = False

    supersede_btn = get_datatable_actions_button(button_text='Supersede',
                                                        button_url=reverse_lazy(
                                                        'admin:fuel_pricing_market_documents_supersede_pricing',
                                                        kwargs={'pk': obj.pk}),
                                                        button_class='btn-outline-primary',
                                                        button_icon='fa-arrow-right',
                                                        button_active=button_active_attr,
                                                        button_modal=False)

    is_published = obj.is_published

    # Display a publish button if all locations have pricing (status OK or Partial PE),
    # Display an unpublish button if every related pricing is published
    if obj.pld_status != 'OK' and obj.pld_status != 'Partial Pricing Expiry':
        row['actions'] = update_btn + supersede_btn
        return row['actions']
    elif is_published:
        action_text = 'Unpublish'
        btn_ico = 'fa-times'
    else:
        action_text = 'Publish'
        btn_ico = 'fa-check'

    publish_depublish_btn = get_datatable_actions_button(button_text=action_text,
                                                        button_url=reverse_lazy(
                                                        'admin:fuel_pricing_market_documents_alter_publication_status',
                                                        kwargs={'pk': obj.pk, 'action': action_text.lower()}),
                                                        button_class='btn-outline-primary',
                                                        button_icon=btn_ico,
                                                        button_active=self.request.user.has_perm(
                                                        'pricing.p_publish'),
                                                        button_modal=True,
                                                        modal_validation=True)

    row['actions'] = update_btn + supersede_btn + publish_depublish_btn

    return row['actions']


def normalize_fraction(d):
    if d is not None:
        normalized = d.normalize()
        sign, digit, exponent = normalized.as_tuple()
        return normalized if exponent <= 0 else normalized.quantize(1)
    else:
        return ''

def find_decimals(value):
    return (abs(Decimal(str(value)).as_tuple().exponent))

def get_band_tolerance(decimal_places):
    return 1 if decimal_places == 0 else Decimal(1) / Decimal('1' + '0' * decimal_places)
