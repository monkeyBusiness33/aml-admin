import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.forms import DecimalField, IntegerField, widgets
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import FormView

from organisation.models import Organisation
from pricing.forms import FuelPricingCalculationFormSet
from pricing.models import PricingCalculationRecord
from pricing.utils.fuel_pricing_calculation import FuelPricingScenario, ResultsSerializer
from user.mixins import AdminPermissionsMixin
from core.utils.datatables_functions import get_datatable_actions_button, get_fontawesome_icon


class FuelPricingCalculationView(AdminPermissionsMixin, FormView):
    context = None
    airport = None
    template_name = 'suppliers_fuel_cost_estimate.html'
    permission_required = ['pricing.p_view']
    form_class = FuelPricingCalculationFormSet

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if self.request.POST.get('airport'):
            self.context = 'Airport'
            self.airport = Organisation.objects.get(pk=self.request.POST.get('airport'))
        else:
            self.context = 'Suppliers'
            self.airport = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'airport': self.airport})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculation-related functionality
        metacontext = {
            'page_id': 'fuel_pricing_calculation',
            'btn_text': 'Calculate Pricing Scenario',
            'form_submit_url': '{% url "admin:fuel_pricing" %}',
        }

        context['formset'] = FuelPricingCalculationFormSet(
            form_kwargs={'context': self.context, 'airport': self.airport}
        )

        context['metacontext'] = metacontext
        context['context'] = self.context
        context['airport'] = None

        return context

    def post(self, request, *args, **kwargs):
        formset = FuelPricingCalculationFormSet(
            request.POST,
            form_kwargs={'context': self.context, 'airport': self.airport}
        )
        form = formset.forms[0]

        # Add dynamically created currency override fields to form
        for key, field in request.POST.items():
            if key.startswith('new_xr_'):
                form.fields[key] = DecimalField(required=False, disabled=True, initial=field, min_value=0)
            elif key == 'src_calculation_id':
                form.fields[key] = IntegerField(required=True, disabled=True, initial=field)

        if formset.forms[0].is_valid():
            return self.form_valid(formset.forms[0])
        else:
            return self.form_invalid(formset.forms[0])

    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors}, status=422)

    def form_valid(self, form):
        self.request.session['results'] = []
        data = form.cleaned_data

        is_rerun = bool(int(self.request.POST.get('is_rerun')))
        xr_overrides = {}

        if is_rerun and 'src_calculation_id' in data:
            # First gather previously used rates from source calculation
            src_calculation = PricingCalculationRecord.objects.get(pk=data['src_calculation_id'])
            for pair, rate in src_calculation.scenario['used_currency_rates'].items():
                xr_overrides[tuple(json.loads(pair))] = {
                    'rate': Decimal(rate['rate']),
                    'src': rate['src'],
                    'timestamp': rate['timestamp'],
                }

            # Override any currency pairs with rates provided by user
            for key, value in data.items():
                if key.startswith('new_xr_') and value is not None:
                    curr_from, curr_to = key.split('_')[-2:]
                    xr_overrides[(curr_from, curr_to)] = {
                        'rate': value.quantize(Decimal('0.000001'), ROUND_HALF_UP),
                        'src': 'MAN',
                        'timestamp': None,
                    }

        # Get airport (from airport page or from form field)
        if self.context == 'Airport':
            airport = Organisation.objects.filter(airport_details__organisation_id=self.airport.pk).first()
        else:
            airport = data['location']

        # Build pricing scenario and calculate all results
        pricing_scenario = FuelPricingScenario(
            airport,
            data,
            data['uplift_datetime'] if not is_rerun else datetime.strptime(
                src_calculation.scenario['validity_datetime_utc'], '%Y-%m-%d %H:%M:%S'),
            is_rerun,
            xr_overrides
        )

        results = pricing_scenario.get_results()

        # Store scenario and results in DB
        record = PricingCalculationRecord(
            scenario=pricing_scenario.serialize(),
            results=[ResultsSerializer().serialize(row) for row in results]
        )
        record.save()

        # Generate action elements for each table row
        for row in results:
            if row['delivery_method']:
                row['delivery_method_str'] = row['delivery_method']
            elif row['excluded_delivery_methods']:
                dm_list = sorted([str(m) for m in row['excluded_delivery_methods']])
                row['delivery_method_str'] = 'All, except ' + ', '.join(dm_list[:-1]) \
                                             + (' and ' if len(dm_list) > 1 else '') \
                                             + dm_list[-1]
            else:
                row['delivery_method_str'] = 'All'

            if row['apron_specific_pricing']:
                row['apron_specific_str'] = row['apron_specific_pricing']['name']
            elif row['excluded_aprons']:
                apron_list = sorted([str(m) for m in row['excluded_aprons']])
                row['apron_specific_str'] = 'All, except ' + ', '.join(apron_list[:-1]) \
                                             + (' and ' if len(apron_list) > 1 else '') \
                                             + apron_list[-1]
            else:
                row['apron_specific_str'] = 'All'


            view_btn = get_datatable_actions_button(button_text='',
                                                    button_url=reverse_lazy(
                                                        'admin:fuel_pricing_calculation_details', kwargs={
                                                            'key': f"{record.pk}-{row['key']}"
                                                        }),

                                                    button_class='fa-eye',
                                                    button_active=self.request.user.has_perm('pricing.p_view'),
                                                    button_modal=True,
                                                    modal_validation=True,
                                                    button_modal_size="#modal-xl")

            row['view_btn'] = view_btn

            if row['issues']:
                issues_html = f'<ul>{"".join([f"<li><span class=tooltip-issue>{issue}</span></li>" for issue in row["issues"]])}</ul>'

                caution_icon = get_fontawesome_icon(
                    icon_name='exclamation-triangle',
                    tooltip_text=issues_html,
                    tooltip_placement='left',
                    tooltip_enable_html=True)

                row['caution_icon'] = caution_icon

            if row['handler_specific_pricing']:
                handler_icon = get_fontawesome_icon(
                    icon_name='warehouse',
                    tooltip_text=f"Handler-specific pricing for <b>{row['handler_specific_pricing']['name']}</b>",
                    tooltip_placement='left',
                    tooltip_enable_html=True)

                row['handler_icon'] = handler_icon

            if row['apron_specific_pricing']:
                apron_icon = get_fontawesome_icon(
                    icon_name='parking',
                    tooltip_text=f"Apron-specific pricing for <b>{row['apron_specific_pricing']['name']}</b>",
                    tooltip_placement='left',
                    tooltip_enable_html=True)

                row['apron_icon'] = apron_icon

        context = {}
        context['results'] = results
        context['results_pk'] = record.pk

        calculation_id_field = IntegerField(
            required=True, disabled=True, initial=record.pk, widget=widgets.HiddenInput()
        ).widget.render('src_calculation_id', record.pk)

        used_xr = pricing_scenario.used_currency_rates
        xr_form_rows = []

        for codes, rate in used_xr.items():
            xr_form_rows.append({
                'curr_codes': ' -> '.join(codes),
                'curr_xr': DecimalField(required=False, label='Calculated FX Rate',
                                        widget=widgets.NumberInput(attrs={
                                            'min': 0,
                                            'step': 0.000001,
                                            'class': 'form-control auto-round-to-step',
                                            'disabled': 'disabled',
                                        })).widget.render(f'curr_xr_{codes[0]}_{codes[1]}',
                                                          Decimal(rate['rate']).quantize(Decimal('0.000001'))),
                'new_xr': DecimalField(required=False, label='Override FX Rate',
                                       widget=widgets.NumberInput(attrs={
                                           'min': 0,
                                           'step': 0.000001,
                                           'class': 'form-control auto-round-to-step',
                                       })).widget.render(f'new_xr_{codes[0]}_{codes[1]}', None)
            })

        return JsonResponse({
            'results': render_to_string('results_page.html', context=context, request=self.request),
            'currency_xr_form': render_to_string(
                'fuel_pricing_calculation_override_xr_form_body.html',
                context={'calculation_id_field': calculation_id_field, 'form_rows': xr_form_rows},
                request=self.request
            ) if xr_form_rows else None,
        }, status=200)
