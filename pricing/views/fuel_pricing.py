import json
from datetime import datetime
from decimal import Decimal

from django.shortcuts import get_object_or_404
from bootstrap_modal_forms.generic import BSModalReadView

from core.utils.datatables_functions import get_fontawesome_icon
from user.mixins import AdminPermissionsMixin
from pricing.models import FuelPricingScenario, PricingCalculationRecord


class FuelPricingCalculationDetailsView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'fuel_pricing_calculation_details_modal.html'
    model = FuelPricingScenario
    context_object_name = 'pricing'
    permission_required = ['pricing.p_view']

    @staticmethod
    def match_tax_components(existing_comp, new_comp):
        # Don't merge taxes included in pricing with regular ones
        if existing_comp['inc_in_pricing'] != new_comp['inc_in_pricing']:
            return False

        # Don't merge taxes with exemption possibility with regular ones
        # if existing_comp['exemption_available_with_cert'] != new_comp['exemption_available_with_cert']:
        #     return False

        if new_comp['percentage'] is not None:
            return new_comp['percentage'] == existing_comp['percentage']

        if new_comp['unit_price'] is not None:
            return new_comp['unit_price'] == existing_comp['unit_price'] \
                and new_comp['original_pricing_unit'] == existing_comp['original_pricing_unit']

    def get_object(self, *args, **kwargs):
        results_id, row_key = self.kwargs['key'].split('-')

        record = get_object_or_404(PricingCalculationRecord, pk=results_id)

        scenario = record.scenario
        results = record.results

        # Merge components based on the same percentage / application method
        # This is done for display only, as in some calculations we need to apply
        # taxable taxes on part of the base tax only (e.g. when it applies to a specific
        # fee category only), so this data needs to be preserved when collecting results
        for row in results:
            for tax_name in row['taxes']['list']:
                for source in ['official', 'supplier']:
                    if source not in row['taxes']['list'][tax_name]:
                        continue

                    all_components = row['taxes']['list'][tax_name][source]['components']
                    merged_components = []

                    for tax_component in all_components:
                        matching_component = next(filter(
                            lambda x: self.match_tax_components(x, tax_component), merged_components),
                            None)

                        if matching_component:
                            if matching_component['base'] is not None:
                                matching_component['base'] += tax_component['base']
                            else:
                                matching_component['base'] = tax_component['base']

                            matching_component['amount'] = Decimal(matching_component['amount']) \
                                                           + Decimal(tax_component['amount'])

                            # Also merge all tax base components to display a list of what each tax is based on
                            new_base_comps = tax_component['base_components']
                            base_comps = matching_component['base_components']

                            if new_base_comps.get('fuel'):
                                base_comps['fuel'] = True
                            if new_base_comps.get('fees'):
                                base_comps['fees'] = base_comps.get('fees', []) + new_base_comps['fees']
                            if new_base_comps.get('taxes'):
                                base_comps['taxes'] = base_comps.get('taxes', []) + new_base_comps['taxes']
                        else:
                            tax_component['amount'] = Decimal(tax_component['amount'])
                            merged_components.append(tax_component)

                        row['taxes']['list'][tax_name][source]['components'] = merged_components

        row_obj = next(filter(lambda x: x['key'] == row_key, results))

        # Prepare currency conversion rates for display
        row_obj['currency_rates_display'] = {}

        for curr_codes, rate in row_obj['used_currency_rates'].items():
            if rate['timestamp']:
                rate['timestamp'] = datetime.fromtimestamp(rate['timestamp']).strftime('%Y-%m-%d %H:%M:%SZ')

            row_obj['currency_rates_display'][tuple(json.loads(curr_codes))] = rate

        # Generate HTML for tooltips in modal
        if row_obj['fuel_price']['notes']:
            notes_html = f'<ul>{"".join([f"<li><span class=tooltip-issue>{note}</span></li>" for note in row_obj["fuel_price"]["notes"]])}</ul>'

            notes_icon = get_fontawesome_icon(
                icon_name='info-circle',
                tooltip_text=notes_html,
                tooltip_placement='right',
                tooltip_enable_html=True)

            row_obj['fuel_price']['notes_icon'] = notes_icon

        for _, fee in row_obj['fees']['list'].items():
            if fee['notes']:
                notes_html = f'<ul>{"".join([f"<li><span class=tooltip-issue>{note}</span></li>" for note in fee["notes"]])}</ul>'

                notes_icon = get_fontawesome_icon(
                    icon_name='info-circle',
                    tooltip_text=notes_html,
                    tooltip_placement='right',
                    tooltip_enable_html=True)

                fee['notes_icon'] = notes_icon

        for _, tax in row_obj['taxes']['list'].items():
            for tax_source in ('official', 'supplier'):
                if tax_source not in tax:
                    continue

                for comp in tax[tax_source]['components']:
                    if comp['inc_in_pricing']:
                        continue

                    base_dict = comp.get('base_components')

                    if base_dict:
                        base_note = "<ul><li>This tax rate applies on the following items:<ul>"

                        if base_dict.get('fuel'):
                            base_note += "<li>Total fuel price</li>"

                        if base_dict.get('fees'):
                            base_note += f"<li>Fees: <ul><li>{'</li><li>'.join(set(base_dict.get('fees')))}</li></ul>"

                        if base_dict.get('taxes'):
                            base_note += f"<li>Taxes: <ul><li>{'</li><li>'.join(set(base_dict.get('taxes')))}</li></ul>"

                        base_note += '</li></ul>'

                        notes_icon = get_fontawesome_icon(
                            icon_name='info-circle',
                            tooltip_text=base_note,
                            tooltip_placement='right',
                            tooltip_enable_html=True)

                        comp['notes_icon'] = notes_icon

        return scenario, row_obj

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['scenario'], context['results_row'] = self.get_object()

        metacontext = {
            'title': f'Supplier Fuel Pricing Details',
            'icon': 'fa-eye',
        }

        context['metacontext'] = metacontext

        return context
