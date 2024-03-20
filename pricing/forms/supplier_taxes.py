from django.db.models import Q
from django import forms
from django.forms import widgets
from django_select2 import forms as s2forms
from django.forms import BaseModelFormSet, modelformset_factory

from core.models import Country, GeographichFlightType
from organisation.models.organisation import Organisation
from pricing.form_widgets import TaxPickWidget, TaxRulePickWidget, TaxRuleExceptionPickWidget
from pricing.models import ChargeBand, Tax, TaxApplicationMethod, TaxRule, TaxRuleException
from pricing.utils.fuel_pricing_market import normalize_fraction
from pricing.utils.tax import check_overlap_with_existing_taxes, crosscheck_with_taxable_taxes, \
    crosscheck_with_existing_children, validate_band_rows


# Same as for the Fuel Pricing
class SupplierTaxExceptionForm(forms.ModelForm):
    charging_method = forms.ChoiceField(
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select a Charging Method'}
        )
    )

    application_method = TaxApplicationMethod.fixed_cost_application_method.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control'}
        )
    )

    fuel_pricing_unit = TaxApplicationMethod.fuel_pricing_unit.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control'}
        )
    )

    band_pricing_amount = forms.DecimalField(required=False,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

    is_taxed_by_vat = forms.BooleanField(
        required=False,
        label='Taxed By Official VAT?',
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input d-block'})
    )

    is_taxed_by_exception = forms.BooleanField(
        required=False,
        label='Taxed By Exception VAT?',
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input d-block'})
    )

    # Supersede specifics
    current_tax_rate = forms.DecimalField(required=False,
                                        widget=widgets.NumberInput(attrs={
                                            'class': 'form-control set-width',
                                            'disabled': 'disabled'
                                        })
                                        )

    no_change = forms.BooleanField(initial=False, required=False,
                                   widget=widgets.CheckboxInput(attrs={
                                       'class': 'form-check-input d-block no-change checkbox-align'
                                   })
                                   )

    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', None)
        self.document = kwargs.pop('document', None)
        self.new_document = kwargs.pop('new_document', None)
        self.document_type = kwargs.pop('doc_type', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Supersede':
            pass
        else:
            self.fields.pop('valid_to')

        if self.context == 'Create':
            self.fields['charging_method'].initial = 'Percentage'
            # If initial is not set, then all forms are going to have changed_data

        self.fields['taxable_tax'].required = False
        self.fields['taxable_exception'].required = False

        if self.document_type == 'agreement':
            airports_qs = Organisation.objects.filter(id__in=self.document.all_pricing_location_pks)
        else:
            airports_qs = Organisation.objects.filter(id__in=self.document.pld_at_location.all().values('location'))

        country_qs = Country.objects.filter(id__in=airports_qs.values('details__country'))

        self.fields['applies_to_fuel'].initial = True

        self.fields['exception_airport'].queryset = airports_qs
        self.fields['exception_airport'].label_from_instance = self.airport_label_from_instance

        self.fields['exception_country'].queryset = country_qs
        self.fields['exception_country'].empty_label = None

        self.fields['charging_method'].choices = [('Fixed', 'Fixed Cost'),
                                                  ('Fixed-Fuel', 'Fixed Cost (Fuel Based)'),
                                                  ('Percentage', 'Percentage of Net Price')]

        # Temporary restrictions, based on LP's specification
        self.fields['band_1_type'].queryset = ChargeBand.objects.filter(type__in=['WB', 'FU'])
        self.fields['band_2_type'].queryset = ChargeBand.objects.filter(type__in=['WB', 'FU'])
        self.fields['geographic_flight_type'].queryset = GeographichFlightType.objects.filter(
            code__in=['ALL', 'INT', 'DOM'])
        self.fields['geographic_flight_type'].label = 'Geographic Flight Type'

        self.fields['application_method'].label_from_instance = self.method_label_from_instance
        self.fields['fuel_pricing_unit'].label_from_instance = self.method_label_from_instance
        self.fields['specific_fuel_cat'].label_from_instance = self.specific_fuel_cat_label_from_instance

        if self.context == 'Edit' or self.context == 'Supersede':
            if self.instance.tax_unit_rate is not None:
                if getattr(self.instance.tax_application_method, 'fixed_cost_application_method') is not None:
                    self.fields['charging_method'].initial = 'Fixed'
                    self.fields[
                        'application_method'].initial = self.instance.tax_application_method.fixed_cost_application_method
                else:
                    self.fields['charging_method'].initial = 'Fixed-Fuel'
                    self.fields['fuel_pricing_unit'].initial = self.instance.tax_application_method.fuel_pricing_unit
            else:
                self.fields['charging_method'].initial = 'Percentage'

        if self.context == 'Edit':
            if self.instance.taxable_tax:
                self.fields['is_taxed_by_vat'].initial = True

            if self.instance.taxable_exception:
                self.fields['is_taxed_by_exception'].initial = True

            if self.instance.band_1_start is not None or self.instance.band_2_start is not None:
                self.fields[
                    'band_pricing_amount'].initial = self.instance.tax_unit_rate if self.instance.tax_unit_rate is not None else self.instance.tax_percentage

    @staticmethod
    def airport_label_from_instance(obj):
        return f'{obj.airport_details.fullname}'

    @staticmethod
    def method_label_from_instance(obj):
        if hasattr(obj, 'name_override'):
            return f'{obj.name_override}'
        else:
            return f'{obj.description}'

    @staticmethod
    def specific_fuel_cat_label_from_instance(obj):
        return f'{obj.name}'

    class Meta:
        model = TaxRuleException
        fields = ['applies_to_fuel', 'applies_to_fees', 'applies_to_private', 'applies_to_commercial',
                  'pax_must_stay_aboard', 'waived_for_tech_stop',
                  'band_1_type', 'band_1_start', 'band_1_end', 'band_2_type', 'band_2_start', 'band_2_end',
                  'valid_from', 'valid_to', 'exception_airport', 'specific_fuel', 'specific_fuel_cat',
                  'specific_fee_category', 'taxable_exception', 'taxable_tax', 'applicable_flight_type',
                  'geographic_flight_type', 'tax_unit_rate', 'tax_percentage',
                  'charging_method', 'application_method', 'fuel_pricing_unit', 'band_pricing_amount',
                  'is_taxed_by_vat',
                  'is_taxed_by_exception', 'current_tax_rate', 'exception_country', 'comments',
                  'exemption_available_with_cert']

        widgets = {
            'applies_to_fuel': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_fees': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'pax_must_stay_aboard': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'waived_for_tech_stop': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'exemption_available_with_cert': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'band_1_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'band_1_start': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'band_1_end': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'band_2_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'band_2_start': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'band_2_end': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'valid_from': widgets.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'valid_to': widgets.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'exception_airport': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Country or an Airport'
            }),
            'exception_country': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Country or an Airport',
            }),
            'specific_fuel': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Specific Fuel'
            }),
            'specific_fuel_cat': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Specific Fuel Cat.'
            }),
            'specific_fee_category': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Specific Fee Category'
            }),
            'taxable_exception': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Tax Exception that applies to this tax'
            }),
            'taxable_tax': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select an Official Tax that applies to this tax'
            }),
            'applicable_flight_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Flight Type'
            }),
            'geographic_flight_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a Destination Type'
            }),
            'tax_unit_rate': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'tax_percentage': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'comments': widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }

    def is_valid(self):
        is_valid = super().is_valid()

        for field in self.errors:
            if field != '__all__':
                if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs[
                    'class']:
                    self.fields[field].widget.attrs['class'] += ' is-invalid'
                elif 'class' not in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid


class BaseSupplierTaxExceptionFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.related_entries = kwargs.pop('related_entries', None)
        self.data = kwargs.pop('data', None)  # Tax form data
        self.context = kwargs.pop('context', None)
        self.document = kwargs.pop('document', None)
        self.new_document = kwargs.pop('new_document', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.instance = kwargs.pop('instance', None)
        self.tax_formset = kwargs.pop('tax_formset', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Supersede':
            if self.document_type == 'agreement':
                locations = self.document.all_pricing_location_pks
            else:
                locations = self.document.pld_at_location.all().values_list('location', flat=True)

            self.queryset = TaxRuleException.objects.filter(
                parent_entry=None,
                exception_organisation=self.document.supplier,
                exception_airport__in=locations,
                deleted_at__isnull=True,
                valid_ufn=True).order_by('taxable_exception')

            for form in self.forms:
                formatted_pricing = ''
                if form['tax_unit_rate'].initial is not None:
                    formatted_pricing = normalize_fraction(form['tax_unit_rate'].initial)
                elif form['tax_percentage'].initial is not None:
                    formatted_pricing = normalize_fraction(form['tax_percentage'].initial)

                form['current_tax_rate'].initial = formatted_pricing
                form['valid_from'].initial = ''

                if form.instance.tax_unit_rate is not None:
                    if getattr(form.instance.tax_application_method, 'fixed_cost_application_method') is not None:
                        form['charging_method'].initial = 'Fixed'
                        form['application_method'].initial = \
                            form.instance.tax_application_method.fixed_cost_application_method

                    elif getattr(form.instance.tax_application_method, 'fuel_pricing_unit') is not None:
                        form['charging_method'].initial = 'Fixed-Fuel'
                        form['fuel_pricing_unit'].initial = form.instance.tax_application_method.fuel_pricing_unit

                else:
                    form['charging_method'].initial = 'Percentage'

        elif self.context == 'Edit':
            self.queryset = TaxRuleException.objects.filter(id=self.instance.pk)
        else:
            self.queryset = TaxRuleException.objects.none()

        if self.context != 'Supersede':

            if self.context == 'Edit':
                if self.document_type == 'agreement':
                    exception_qs = TaxRuleException.objects.filter(deleted_at__isnull=True,
                                                                   valid_ufn=True,
                                                                   parent_entry=None,
                                                                   source_agreement__supplier=self.document.supplier) \
                        .exclude(id=self.instance.pk)
                else:
                    exception_qs = TaxRuleException.objects.filter(deleted_at__isnull=True,
                                                                   valid_ufn=True,
                                                                   parent_entry=None,
                                                                   related_pld__supplier=self.document.supplier) \
                        .exclude(id=self.instance.pk)
            else:
                if self.document_type == 'agreement':
                    exception_qs = TaxRuleException.objects.filter(deleted_at__isnull=True,
                                                                   parent_entry=None,
                                                                   valid_ufn=True,
                                                                   source_agreement__supplier=self.document.supplier)
                else:
                    exception_qs = TaxRuleException.objects.filter(deleted_at__isnull=True,
                                                                   parent_entry=None,
                                                                   valid_ufn=True,
                                                                   related_pld__supplier=self.document.supplier)

            for value, form in enumerate(self.forms):
                # Get Only % based VAT
                form.fields['taxable_tax'].widget = TaxRulePickWidget(
                    queryset=TaxRule.objects.filter(tax_rate_percentage__isnull=False, deleted_at__isnull=True),
                    dependent_fields={f'new-tax-rule-exception-{value}-exception_airport': 'selected_airport'})
                form.fields['taxable_exception'].widget = TaxRuleExceptionPickWidget(
                    queryset=exception_qs,
                    dependent_fields={f'new-tax-rule-exception-{value}-exception_airport': 'exception_airport'}
                )

        for form in self.forms:
            form['band_1_start'].initial = normalize_fraction(form['band_1_start'].initial)
            form['band_1_end'].initial = normalize_fraction(form['band_1_end'].initial)
            form['band_2_start'].initial = normalize_fraction(form['band_2_start'].initial)
            form['band_2_end'].initial = normalize_fraction(form['band_2_end'].initial)
            form['band_pricing_amount'].initial = normalize_fraction(form['band_pricing_amount'].initial)
            form['taxable_tax'].initial = form.instance.taxable_tax
            form['taxable_exception'].initial = form.instance.taxable_exception

    def add_fields(self, form, index):
        super(BaseSupplierTaxExceptionFormSet, self).add_fields(form, index)

        form.fields[f'confirm_checkbox'] = forms.BooleanField(required=False, widget=forms.CheckboxInput())

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'band_1_start-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=False,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_1_end-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=False,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_2_start-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=False,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_2_end-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=False,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

                        if self.context == 'Supersede':
                            related_entries = TaxRuleException.objects.filter(parent_entry=form['id'].initial) \
                                .order_by('band_1_start', 'band_2_start')
                            if value < related_entries.count():
                                form.fields[f'current_tax_rate-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(
                                                         attrs={'step': 0.0001, 'class': 'form-control',
                                                                'disabled': 'disabled'}))
                            else:
                                form.fields[f'current_tax_rate-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(
                                                         attrs={'step': 0.0001, 'class': 'form-control d-none',
                                                                'disabled': 'disabled'}))

                        form.fields[f'band_pricing_amount-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

        elif self.related_entries or self.context == 'Supersede':
            related_entries = TaxRuleException.objects.filter(parent_entry=form['id'].initial).order_by('band_1_start',
                                                                                                        'band_2_start')
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'band_1_start-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=False, initial=normalize_fraction(entry.band_1_start),
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_1_end-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=False, initial=normalize_fraction(entry.band_1_end),
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_2_start-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=False, initial=normalize_fraction(entry.band_2_start),
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_2_end-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=False, initial=normalize_fraction(entry.band_2_end),
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step'}))

                if entry.tax_unit_rate is not None:
                    rate_initial = entry.tax_unit_rate
                else:
                    rate_initial = entry.tax_percentage

                if self.context == 'Supersede':
                    form.fields[f'current_tax_rate-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(rate_initial),
                                         widget=widgets.NumberInput(
                                             attrs={'step': 0.0001, 'class': 'form-control', 'disabled': 'disabled'}))

                form.fields[f'band_pricing_amount-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True,
                                     initial=normalize_fraction(rate_initial) if self.context != 'Supersede' else '',
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step'}))

    def clean(self):
        formset_has_errors = False
        for form_number, form in enumerate(self.forms):

            valid_from = form.cleaned_data.get('valid_from')

            if self.context == 'Supersede':
                if form.cleaned_data.get('no_change'):
                    for error in list(form.errors):
                        del form._errors[error]
                    continue

                if form.cleaned_data.get('DELETE'):
                    if form.cleaned_data.get('valid_to') is None:
                        form.add_error('valid_to', 'Please specify a fee expiration date')
                        raise forms.ValidationError("Expiration date is required")
                    else:
                        for error in list(form.errors):
                            del form._errors[error]
                        continue

                if valid_from and valid_from < form.cleaned_data.get('id').valid_from:
                    form.add_error('valid_from', f'Needs to be later than {form.cleaned_data.get("id").valid_from}')

            # Skip validation of empty forms
            elif self.context == 'Create':
                if form.cleaned_data.get('DELETE'):
                    for error in list(form.errors):
                        del form._errors[error]
                    continue

            # For creation and edition, make sure one and only one of exception country / airport is present
            if form.has_changed() and self.context != 'Supersede':
                if all(
                    [form.cleaned_data.get('exception_country'), form.cleaned_data.get('exception_airport')]):
                    form.add_error('exception_country', "Can't save tax with both specific airport"
                                                        " and country selected")
                if not any(
                    [form.cleaned_data.get('exception_country'), form.cleaned_data.get('exception_airport')]):
                    form.add_error('exception_airport', "Please select a specific airport or country")

                if self.tax_formset:
                    tax_instance = self.tax_formset.forms[form_number].cleaned_data.get('tax_instance')
                    # Also make sure, that if a tax instance is selected, it is valid for the airport / country
                    if tax_instance and form.cleaned_data.get('exception_airport'):
                        if tax_instance.applicable_country != form.cleaned_data['exception_airport'].details.country:
                            self.tax_formset.forms[form_number].add_error(
                                'tax_instance', "This tax does not match selected airport's country")
                            form.add_error('exception_airport', '')

                    if tax_instance and form.cleaned_data.get('exception_country'):
                        if tax_instance.applicable_country != form.cleaned_data['exception_country']:
                            self.tax_formset.forms[form_number].add_error(
                                'tax_instance', "This tax does not match selected country")
                            form.add_error('exception_country', '')


            instances_of_band_1 = 0
            instances_of_band_2 = 0

            has_band_pricing = False
            for field, value in form.cleaned_data.items():
                if 'band_1_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_1 += 1
                if 'band_2_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_2 += 1

            charging_method = form.cleaned_data.get('charging_method')
            band_amount = form.cleaned_data.get('band_pricing_amount')
            unit_rate = form.cleaned_data.get('tax_unit_rate')
            percentage_rate = form.cleaned_data.get('tax_percentage')
            taxable_tax = form.cleaned_data.get('taxable_tax')
            taxable_exception = form.cleaned_data.get('taxable_exception')

            if form.cleaned_data.get('specific_fee_category') and form.cleaned_data.get('specific_fuel'):
                formset_has_errors = True
                form.add_error('specific_fee_category', "Can't save tax with both specific fuel and fee specified")

            if form.cleaned_data.get('specific_fuel_cat') and form.cleaned_data.get('specific_fuel'):
                formset_has_errors = True
                form.add_error('specific_fuel_cat', "Can't save tax with both specific fuel and fuel cat. specified")

            if form.cleaned_data.get('specific_fuel_cat') and form.cleaned_data.get('specific_fee_category'):
                formset_has_errors = True
                form.add_error('specific_fuel_cat',
                               "Can't save tax with both specific fuel cat. and specific fee cat. specified")

            if band_amount is None and has_band_pricing and percentage_rate is None and unit_rate is None:
                formset_has_errors = True
                form.add_error('band_pricing_amount', 'Please Specify an Amount')

            if charging_method == 'Fixed':
                if unit_rate is None and not has_band_pricing and not self.context == 'Supersede':
                    formset_has_errors = True
                    form.add_error('tax_unit_rate', 'Please Specify a Unit Rate')
                if form.cleaned_data.get('application_method') is None:
                    formset_has_errors = True
                    form.add_error('application_method', 'Please Specify an Application Method')

            elif charging_method == 'Fixed-Fuel':
                if unit_rate is None and not has_band_pricing and not self.context == 'Supersede':
                    formset_has_errors = True
                    form.add_error('tax_unit_rate', 'Please Specify a Unit Rate')

                if form.cleaned_data.get('fuel_pricing_unit') is None:
                    formset_has_errors = True
                    form.add_error('fuel_pricing_unit', 'Please Specify an Application Method')

            elif charging_method == 'Percentage':
                if percentage_rate is None and not has_band_pricing and not self.context == 'Supersede':
                    formset_has_errors = True
                    form.add_error('tax_percentage', 'Please Specify a Unit Rate')

            cleaned_data_copy = form.cleaned_data.copy()

            if has_band_pricing:
                if form.cleaned_data.get('band_1_type') is None and instances_of_band_1 != 0:
                    formset_has_errors = True
                    form.add_error('band_1_type', 'Please Specifiy a Condition Type')

                if form.cleaned_data.get('band_2_type') is None and instances_of_band_2 != 0:
                    formset_has_errors = True
                    form.add_error('band_2_type', 'Please Specifiy a Condition Type')

                if form.cleaned_data.get('band_1_type') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band_1', 'decimal')

                if form.cleaned_data.get('band_2_type') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band_2', 'decimal')

                for field, value in cleaned_data_copy.items():
                    if 'band_pricing' in field and value is None:
                        formset_has_errors = True
                        form.add_error(field, '')

            if form.cleaned_data.get('is_taxed_by_vat') and self.context != 'Supersede':
                has_mismatch = crosscheck_with_taxable_taxes(form, has_band_pricing,
                                                             instances_of_band_1, instances_of_band_2,
                                                             taxable_tax, 'official', form_number)

            if form.cleaned_data.get('is_taxed_by_exception') and self.context != 'Supersede':
                has_mismatch = crosscheck_with_taxable_taxes(form, has_band_pricing,
                                                             instances_of_band_1, instances_of_band_2,
                                                             taxable_exception, 'exceptions', form_number)

            # Django removes the k/v pair from form.cleaned_data so we can't proceed and also stacking errors
            # would confuse the user
            if form_number == len(self.forms) - 1 and (formset_has_errors or form.errors):
                return

            # Not using for supersede (we have missing fields)
            if self.context != 'Supersede' and not form.errors:
                # Check if tax already exists
                applies_to_fees = form.cleaned_data.get('applies_to_fees')
                applies_to_fuel = form.cleaned_data.get('applies_to_fuel')
                applies_to_private = form.cleaned_data.get('applies_to_private')
                applies_to_commercial = form.cleaned_data.get('applies_to_commercial')
                valid_from = form.cleaned_data.get('valid_from')
                pax_stays = form.cleaned_data.get('pax_must_stay_aboard')
                tech_stop = form.cleaned_data.get('waived_for_tech_stop')
                charging_method = form.cleaned_data.get('tax_rule_charging_method')
                band_amount = form.cleaned_data.get('band_pricing_amount')
                exception_airport = form.cleaned_data.get('exception_airport')
                exception_country = form.cleaned_data.get('exception_country')

                category_query = ''
                if self.data.get(f'tax-{form_number}-category') is None:
                    if hasattr(self.instance, 'pk'):
                        category_query = self.instance.tax.category
                    else:
                        tax_instance = Tax.objects.filter(id=self.data.get(f'tax-{form_number}-tax_instance'))
                        if tax_instance.exists():
                            category_query = tax_instance[0].category
                else:
                    category_query = self.data.get(f'tax-{form_number}-category')

                # Get all relevant rules, if any core properties mismatch, then we don't have an overlap
                # Shortcircuits empty forms
                if category_query == '':
                    continue
                existing_exceptions = TaxRuleException.objects.filter(
                    Q(deleted_at__isnull=True),
                    Q(valid_ufn=True),
                    Q(exception_organisation=self.document.supplier),
                    Q(exception_airport=exception_airport),
                    Q(exception_country=exception_country),
                    Q(tax__category=category_query),
                    Q(applies_to_private=applies_to_private) |
                    Q(applies_to_commercial=applies_to_commercial),
                    Q(applies_to_fuel=applies_to_fuel) |
                    Q(applies_to_fees=applies_to_fees),
                    Q(waived_for_tech_stop=tech_stop),
                    Q(pax_must_stay_aboard=pax_stays)).exclude(~Q(parent_entry=None))

                if self.instance is not None:
                    existing_exceptions = existing_exceptions.exclude(id=self.instance.pk)

                if existing_exceptions.exists():
                    for exception in existing_exceptions:
                        check_overlap_with_existing_taxes(form, exception, form.cleaned_data, valid_ufn=False,
                                                          context='exception')

            if not form.errors and \
                (self.context == 'Edit' or (self.context == 'Supersede' and not form.cleaned_data.get('no_change'))):
                # Check if editing would make related taxed! supplier defined taxes invalid

                if self.context == 'Edit':
                    instance = self.instance
                else:
                    instance = form.cleaned_data.get('id')

                taxed_exceptions = TaxRuleException.objects.filter(taxable_exception=instance, parent_entry=None,
                                                                   deleted_at__isnull=True)

                reassign_exceptions, changes_exceptions = crosscheck_with_existing_children(form,
                                                                                            taxed_exceptions,
                                                                                            has_band_pricing,
                                                                                            instances_of_band_1,
                                                                                            instances_of_band_2,
                                                                                            'exception', form_number,
                                                                                            'existing', self.context)

                has_official_mismatch = False
                has_exception_mismatch = False

                if changes_exceptions and self.context == 'Edit':
                    if form.cleaned_data.get('confirm_checkbox'):
                        for entry in changes_exceptions:
                            entry.taxable_exception = None
                            child_entries = entry.child_entries.all()
                            for child_entry in child_entries:
                                child_entry.taxable_except = None
                                child_entry.save()
                            entry.save()
                    else:
                        form.cleaned_data['exception_entity_id_list'] = changes_exceptions
                        form.add_error('confirm_checkbox', '')

                elif self.context == 'Supersede':
                    # Also check the entry vs. official taxes
                    current_instance = form.cleaned_data.get('id')
                    if taxable_tax:
                        has_official_mismatch = crosscheck_with_taxable_taxes(form, has_band_pricing,
                                                                              instances_of_band_1, instances_of_band_2,
                                                                              taxable_tax, 'official', form_number,
                                                                              True)

                        if has_official_mismatch:
                            form.cleaned_data[f'form-{form_number}-official_mismatch'] = current_instance
                            if not form.cleaned_data.get('confirm_checkbox'):
                                form.add_error('confirm_checkbox', '')

                    if taxable_exception:
                        has_exception_mismatch = crosscheck_with_taxable_taxes(form, has_band_pricing,
                                                                               instances_of_band_1, instances_of_band_2,
                                                                               taxable_exception, 'exceptions',
                                                                               form_number, True)

                        if has_exception_mismatch:
                            form.cleaned_data[f'form-{form_number}-exception_mismatch'] = current_instance
                            if not form.cleaned_data.get('confirm_checkbox'):
                                form.add_error('confirm_checkbox', '')

                    if changes_exceptions:
                        form.cleaned_data[f'form-{form_number}-exception_entity_list'] = changes_exceptions
                        if not form.cleaned_data.get('confirm_checkbox'):
                            form.add_error('confirm_checkbox', '')

                    # Then remove said entities from the superseded taxes (during saving)


NewTaxRuleExceptionFormset = modelformset_factory(TaxRuleException,
                                                  extra=10,
                                                  can_delete=True,
                                                  form=SupplierTaxExceptionForm,
                                                  formset=BaseSupplierTaxExceptionFormSet
                                                  )

TaxRuleExceptionFormset = modelformset_factory(TaxRuleException,
                                               can_delete=True,
                                               extra=0,
                                               form=SupplierTaxExceptionForm,
                                               formset=BaseSupplierTaxExceptionFormSet
                                               )


# Used for the same purposes as the Fuel Pricing form minus superseding
class SupplierTaxForm(forms.ModelForm):
    tax_instance = forms.ModelChoiceField(
        queryset=Tax.objects.all(),
        label='Existing Tax',
        widget=TaxPickWidget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select Tax'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['local_name'].required = False
        self.fields['category'].required = False
        self.fields['tax_instance'].required = False

    class Meta:
        model = Tax
        fields = ['tax_instance', 'local_name', 'short_name', 'category']

        widgets = {
            'local_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'short_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'category': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Category'
            }),
        }

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs[
                'class']:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
            elif 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid


class BaseSupplierTaxFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.document = kwargs.pop('document', None)
        self.new_document = kwargs.pop('new_document', None)
        self.document_type = kwargs.pop('doc_type', None)
        super().__init__(*args, **kwargs)

        if hasattr(self.instance, 'pk') is not False:
            self.queryset = Tax.objects.filter(id=self.instance.tax.pk)

        # On creation
        else:
            self.queryset = Tax.objects.none()
            # for form in self.forms:
            #     form.empty_permitted = True
            # self.forms[0].empty_permitted = False

        for value, form in enumerate(self.forms):
            form.fields['tax_instance'].widget = TaxPickWidget(
                dependent_fields={f'new-tax-rule-exception-{value}-exception_airport': 'selected_airport',
                                  f'new-tax-rule-exception-{value}-exception_country': 'selected_country'})

            if hasattr(self.instance, 'pk'):
                form['tax_instance'].initial = self.instance.tax.id

    def clean(self):
        for form in self.forms:
            if form.has_changed() and not form.cleaned_data.get('tax_instance') and not form.cleaned_data.get(
                'category'):
                form.add_error('tax_instance', 'Select or create a new tax')
        return super().clean()


TaxFormset = modelformset_factory(Tax,
                                  can_delete=True,
                                  extra=0,
                                  form=SupplierTaxForm,
                                  formset=BaseSupplierTaxFormSet
                                  )

NewTaxFormset = modelformset_factory(Tax,
                                     extra=10,
                                     form=SupplierTaxForm,
                                     formset=BaseSupplierTaxFormSet
                                     )
