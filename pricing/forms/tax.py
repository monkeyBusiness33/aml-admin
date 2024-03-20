from datetime import date

from django import forms
from django.db.models import Q
from django.forms import BaseModelFormSet, modelformset_factory, widgets
from django_select2 import forms as s2forms
from bootstrap_modal_forms.forms import BSModalForm

from core.models import GeographichFlightType, Region
from organisation.models import Organisation
from pricing.models.tax import Tax, TaxApplicationMethod, TaxRate, TaxRatePercentage, TaxRule, TaxRuleException, \
    TaxSource
from pricing.models.charge_strucure import ChargeBand
from pricing.utils.fuel_pricing_market import normalize_fraction
from pricing.utils.tax import check_overlap_with_existing_taxes, crosscheck_with_taxable_taxes, \
    taxrule_label_from_instance, crosscheck_with_existing_children, validate_band_rows

class TaxForm(forms.ModelForm):

    tax_instance = forms.ModelChoiceField(
        label='Existing Tax',
        queryset=None,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select Tax'}),
    )

    def __init__(self, *args, **kwargs):
        self.country = kwargs.pop('country', None)
        self.tax_instance = kwargs.pop('tax_instance', None)
        self.type = kwargs.pop('type', None)
        super().__init__(*args, **kwargs)

        self.fields['applicable_region'].required = False

        if self.type == 'regional':
            qs = Tax.objects.filter(applicable_region__country = self.country)
            self.fields['applicable_region'].queryset = Region.objects.filter(country = self.country)
            self.fields['applicable_region'].label_from_instance = self.region_label_from_instance
            if not qs.exists():
                self.fields['applicable_region'].required = True

        elif self.type == 'country':
            qs = Tax.objects.filter(applicable_country = self.country)

        elif self.type == 'airport':
            qs = Tax.objects.filter(Q(applicable_country = self.country) | Q(applicable_region__country = self.country))

        else:
            qs = Tax.objects.filter(Q(category_id = 1), Q(rates__tax_rate_id = 1),
                                    Q(applicable_country = self.country) | Q(applicable_region__country = self.country))

            if qs.exists():
                self.fields['tax_instance'].initial = qs[0]
                self.fields['tax_instance'].disabled = True

        self.fields['tax_instance'].queryset = qs
        self.fields['tax_instance'].label_from_instance = self.tax_instance_label_from_instance

        if self.tax_instance is not None:
            self.fields['tax_instance'].initial = self.tax_instance

        self.fields['local_name'].required = False
        self.fields['category'].required = False
        self.fields['tax_instance'].required = False


    @staticmethod
    def tax_instance_label_from_instance(obj):
        if getattr(obj, 'applicable_region') is not None:
            return f'{obj.local_name} - {obj.category.name} - {obj.applicable_region.name} Region'
        else:
            return f'{obj.local_name} - {obj.category.name}'

    @staticmethod
    def region_label_from_instance(obj):
            if obj.name:
                return f'{obj.name}'
            else:
                return f'{obj.code}'

    class Meta:
        model = Tax
        fields = ['tax_instance', 'local_name', 'short_name', 'category', 'applicable_region']

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
            'applicable_region': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select a New Region'
            }),
        }

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs['class']:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
            elif 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        if not self.cleaned_data.get('tax_instance') and not self.cleaned_data.get('category'):
            raise forms.ValidationError({'tax_instance':'Select or create a new tax'})
        return cleaned_data


class TaxRuleForm(forms.ModelForm):

    tax_rule_charging_method = forms.ChoiceField(
        widget=s2forms.Select2Widget(
        attrs={'class': 'form-control',
               'data-placeholder': 'Select a Charging Method'}
        )
    )

    tax_unit_rate_application_method = TaxApplicationMethod.fixed_cost_application_method.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
        attrs={'class': 'form-control'}
        )
    )

    tax_percentage_rate = TaxRatePercentage.tax_percentage.field.formfield(
        required=False,
        widget=widgets.NumberInput(
        attrs={'class': 'form-control auto-round-to-step'}
        )
    )

    tax_percentage_rate_application_method = TaxRatePercentage.tax_rate.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
        attrs={'class': 'form-control'}
        )
    )

    taxed_by_vat = forms.BooleanField(
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input d-block'})
    )

    fuel_pricing_unit = TaxApplicationMethod.fuel_pricing_unit.field.formfield(
        widget=s2forms.Select2Widget(
        attrs={'class': 'form-control'}
        )
    )

    band_pricing_amount = forms.DecimalField(required=False,
        widget=widgets.NumberInput(attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

    band_method = forms.ModelChoiceField(
        queryset=TaxRate.objects.all(),
        required=False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control'}
        )
    )

    # taxed_by_primary_vat = forms.IntegerField(required=False)

    taxable_tax = forms.ModelChoiceField(
        queryset=TaxRule.objects.none(),
        required = False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select a matching VAT'}
        )
    )

    def __init__(self, *args, **kwargs):
        self.country = kwargs.pop('country', None)
        self.type = kwargs.pop('type', None)
        super().__init__(*args, **kwargs)

        self.fields['applies_to_fuel'].initial = True

        self.fields['tax_rule_charging_method'].choices = [('Fixed', 'Fixed Cost'),
                                                           ('Fixed-Fuel', 'Fixed Cost (Fuel Based)'),
                                                           ('Percentage', 'Percentage of Net Price')]

        self.fields['band_method'].empty_label = None

        # Temporary restrictions, based on LP's specification
        self.fields['band_1_type'].queryset = ChargeBand.objects.filter(type__in = ['WB', 'FU'])
        self.fields['band_2_type'].queryset = ChargeBand.objects.filter(type__in = ['WB', 'FU'])
        self.fields['geographic_flight_type'].queryset = GeographichFlightType.objects.filter(code__in = ['ALL', 'INT', 'DOM'])

        self.fields['taxable_tax'].label_from_instance = self.taxable_tax_label_from_instance
        self.fields['tax_unit_rate_application_method'].label_from_instance = self.method_label_from_instance
        self.fields['tax_percentage_rate_application_method'].label_from_instance = self.method_label_from_instance
        self.fields['fuel_pricing_unit'].label_from_instance = self.pricing_label_from_instance
        self.fields['specific_fuel_cat'].label_from_instance = self.specific_fuel_cat_label_from_instance

        self.fields['taxable_tax'].queryset =\
                                TaxRule.objects.filter(Q(tax_rate_percentage__tax__category__name = 'Value-Added Tax'),
                                                       Q(tax_rate_percentage__tax__applicable_country = self.country),
                                                       Q(tax_rate_percentage__tax_rate__name = 'Standard'),
                                                       Q(parent_entry = None),
                                                       Q(deleted_at__isnull = True),
                                                       Q(specific_airport__isnull = True)).exclude(id = self.instance.id)

        if self.type == 'airport':
            self.fields['specific_airport'].required = True
            self.fields['specific_airport'].queryset = Organisation.objects.filter(details__country = self.country,
                                                                                   details__type_id=8)
            self.fields['specific_airport'].label_from_instance = self.airport_label_from_instance

            self.fields['taxable_tax'].queryset =\
                                TaxRule.objects.filter(Q(tax_rate_percentage__tax__category__name = 'Value-Added Tax'),
                                                       Q(tax_rate_percentage__tax_rate__name = 'Standard'),
                                                       Q(parent_entry = None),
                                                       Q(deleted_at__isnull = True),
                                                       Q(tax_rate_percentage__tax__applicable_country = self.country) |
                                                       Q(tax_rate_percentage__tax__applicable_region__country = self.country))\
                                                .exclude(id = self.instance.id)

        elif self.type == 'regional':
            self.fields['taxable_tax'].queryset =\
                                TaxRule.objects.filter(Q(tax_rate_percentage__tax__category__name = 'Value-Added Tax'),
                                                       Q(tax_rate_percentage__tax_rate__name = 'Standard'),
                                                       Q(parent_entry = None),
                                                       Q(deleted_at__isnull = True),
                                                       Q(specific_airport__isnull = True),
                                                       Q(tax_rate_percentage__tax__applicable_country = self.country) |
                                                       Q(tax_rate_percentage__tax__applicable_region__country = self.country))\
                                                .exclude(id = self.instance.id)


        # There must be a better way to include related fields
        if getattr(self.instance, 'pk') is not None:
            self.fields['taxable_tax'].initial = self.instance.taxable_tax

            if self.instance.tax_application_method:
                if self.instance.tax_application_method.fixed_cost_application_method:
                    self.fields['tax_rule_charging_method'].initial = 'Fixed'
                    self.fields['tax_unit_rate_application_method'].initial = self.instance.tax_application_method.fixed_cost_application_method
                else:
                    self.fields['tax_rule_charging_method'].initial = 'Fixed-Fuel'
                    self.fields['fuel_pricing_unit'].initial = self.instance.tax_application_method.fuel_pricing_unit
            else:
                self.fields['tax_rule_charging_method'].initial = 'Percentage'
                self.fields['tax_percentage_rate'].initial = self.instance.tax_rate_percentage.tax_percentage
                self.fields['tax_percentage_rate_application_method'].initial = self.instance.tax_rate_percentage.tax_rate

            if self.instance.taxable_tax:
                self.fields['taxed_by_vat'].initial = True

            if self.instance.tax:
                amount_to_display = self.instance.tax_unit_rate
            elif self.instance.tax_rate_percentage:
                amount_to_display = self.instance.tax_rate_percentage.tax_percentage

            if self.instance.band_1_start is not None or self.instance.band_2_start is not None:
                self.fields['band_pricing_amount'].initial = amount_to_display


    @staticmethod
    def airport_label_from_instance(obj):
        return f'{obj.airport_details.fullname}'

    @staticmethod
    def method_label_from_instance(obj):
        if hasattr(obj, 'name_override'):
            return f'{obj.name_override}'
        else:
            return f'{obj.name}'

    @staticmethod
    def pricing_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def specific_fuel_cat_label_from_instance(obj):
        return f'{obj.name}'

    @staticmethod
    def taxable_tax_label_from_instance(obj):

       return taxrule_label_from_instance(obj)

    class Meta:
        model = TaxRule
        fields = ['waived_for_tech_stop', 'taxed_by_vat', 'pax_must_stay_aboard',
                  'applies_to_fuel', 'applies_to_fees',
                  'specific_fuel', 'specific_fuel_cat', 'specific_fee_category', 'specific_airport',
                  'band_1_type', 'band_1_start', 'band_1_end', 'band_2_type', 'band_2_start', 'band_2_end',
                  'valid_from', 'valid_to', 'valid_ufn',
                  'applicable_flight_type','geographic_flight_type',
                  'tax_rule_charging_method', 'tax_unit_rate', 'tax_unit_rate_application_method',
                  'tax_percentage_rate', 'tax_percentage_rate_application_method', 'band_pricing_amount',
                  'applies_to_commercial', 'applies_to_private', 'taxable_tax', 'band_method', 'comments',
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
            }),
            'valid_to': widgets.DateInput(attrs={
                'class': 'form-control',
            }),
            'valid_ufn': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'specific_airport': s2forms.Select2Widget(attrs={
                'class': 'form-control',
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
            'comments': widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs['class']:
                    self.fields[field].widget.attrs['class'] += ' is-invalid'
                elif 'class' not in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class TaxSourceForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['name'].required = False


    class Meta:
        model = TaxSource
        fields = ['name', 'file_url', 'web_url']

        widgets = {
            'name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'web_url': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'file_url': widgets.TextInput(attrs={
                'class': 'form-control'
            }),
        }

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs['class']:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
            elif 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class BaseTaxSourceFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.tax_source:
            self.queryset = TaxSource.objects.filter(id = self.instance.tax_source.pk)
        else:
            self.queryset = TaxSource.objects.none()


NewTaxSourceFormset = modelformset_factory(TaxSource,
            extra=10,
            form=TaxSourceForm,
            formset=BaseTaxSourceFormSet
            )

TaxSourceFormset = modelformset_factory(TaxSource,
            extra=1,
            form=TaxSourceForm,
            formset=BaseTaxSourceFormSet
            )


class BaseTaxRuleFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.country = kwargs.pop('country', None)
        self.type = kwargs.pop('type', None)
        self.instance = kwargs.pop('instance', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.related_entries = kwargs.pop('related_entries', None)
        self.tax_form_data = kwargs.pop('data', None)
        super().__init__(*args, **kwargs)

        if hasattr(self.instance, 'pk'):
            self.queryset = TaxRule.objects.filter(id = self.instance.pk)

            for form in self.forms:
                form['band_1_start'].initial = normalize_fraction(form['band_1_start'].initial)
                form['band_1_end'].initial = normalize_fraction(form['band_1_end'].initial)
                form['band_2_start'].initial = normalize_fraction(form['band_2_start'].initial)
                form['band_2_end'].initial = normalize_fraction(form['band_2_end'].initial)
                form['band_pricing_amount'].initial = normalize_fraction(form['band_pricing_amount'].initial)
                form['tax_unit_rate'].initial = normalize_fraction(form['tax_unit_rate'].initial)
                form['tax_percentage_rate'].initial = normalize_fraction(form['tax_percentage_rate'].initial)
                form['band_method'].initial = form['tax_percentage_rate_application_method'].initial

        # On creation
        else:
            self.queryset = TaxRule.objects.none()

    def add_fields(self, form, index):
        super(BaseTaxRuleFormSet, self).add_fields(form, index)

        form.fields[f'confirm_checkbox'] = forms.BooleanField(required=False, widget=widgets.CheckboxInput())
        form.fields[f'new_valid_to_date'] = forms.DateField(required=False,
                                                            widget=widgets.DateInput(attrs=
                                                            {'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}))

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        # Decimal numbers stay for now, as later, other bands that need decimals might be included
                        form.fields[f'band_1_start-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=False,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_1_end-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=False,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_2_start-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=False,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_2_end-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=False,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_pricing_amount-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=True,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

                        form.fields[f'band_method-additional-{form_number}-{value+1}'] = \
                                    forms.ModelChoiceField(required=False, queryset=TaxRate.objects.all(),
                                    widget=s2forms.Select2Widget(attrs={'class': 'form-control'}))

        elif self.related_entries:
            related_entries = TaxRule.objects.filter(parent_entry = form['id'].initial).order_by('band_1_start', 'band_2_start')
            form_number = index
            for value, entry in enumerate(related_entries):
                form.fields[f'band_1_start-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=False, initial=normalize_fraction(entry.band_1_start),
                            widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                              'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_1_end-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=False, initial=normalize_fraction(entry.band_1_end),
                            widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                              'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_2_start-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=False, initial=normalize_fraction(entry.band_2_start),
                            widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                              'class': 'form-control auto-round-to-step'}))

                form.fields[f'band_2_end-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=False, initial=normalize_fraction(entry.band_2_end),
                            widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                              'class': 'form-control auto-round-to-step'}))

                if self.instance.tax:
                    rate_initial = entry.tax_unit_rate
                else:
                    rate_initial = entry.tax_rate_percentage.tax_percentage

                form.fields[f'band_pricing_amount-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=True, initial=normalize_fraction(rate_initial),
                            widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                              'class': 'form-control auto-round-to-step'}))

                if self.instance.tax_rate_percentage:
                    form.fields[f'band_method-additional-{form_number}-{value+1}'] = \
                                forms.ModelChoiceField(required=False, queryset=TaxRate.objects.all(),
                                initial=entry.tax_rate_percentage.tax_rate,
                                widget=s2forms.Select2Widget(attrs={'class': 'form-control'}))

    def clean(self):
        for form_number, form in enumerate(self.forms):
            if form.cleaned_data.get('valid_ufn') == False and form.cleaned_data.get('valid_to') is None:
                form.add_error('valid_to', '')

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
                if 'band_1_start-additional' in field:
                    has_band_pricing = True

            charging_method = form.cleaned_data.get('tax_rule_charging_method')
            band_amount = form.cleaned_data.get('band_pricing_amount')
            unit_rate = form.cleaned_data.get('tax_unit_rate')
            percentage_rate = form.cleaned_data.get('tax_percentage_rate')

            if form.cleaned_data.get('specific_fee_category') and form.cleaned_data.get('specific_fuel'):
                form.add_error('specific_fee_category', "Can't save tax with both specific fuel and fee specified")

            if form.cleaned_data.get('specific_fuel_cat') and form.cleaned_data.get('specific_fuel'):
                form.add_error('specific_fuel_cat', "Can't save tax with both specific fuel and fuel cat. specified")

            if form.cleaned_data.get('specific_fuel_cat') and form.cleaned_data.get('specific_fee_category'):
                form.add_error('specific_fuel_cat',
                               "Can't save tax with both specific fuel cat. and specific fee cat. specified")

            if band_amount is None and has_band_pricing and percentage_rate is None and unit_rate is None:
                    form.add_error('band_pricing_amount', 'Please Specify an Amount')

            if charging_method == 'Fixed':
                if unit_rate is None and not has_band_pricing:
                   form.add_error('tax_unit_rate', 'Please Specify a Unit Rate')
                if form.cleaned_data.get('tax_unit_rate_application_method') is None:
                    form.add_error('tax_unit_rate_application_method', 'Please Specify an Application Method')

            elif charging_method == 'Fixed-Fuel':
                if unit_rate is None and not has_band_pricing:
                    form.add_error('tax_unit_rate', 'Please Specify a Unit Rate')
                if form.cleaned_data.get('fuel_pricing_unit') is None:
                    form.add_error('fuel_pricing_unit', 'Please Specify an Application Method')

            elif charging_method == 'Percentage':
                if percentage_rate is None and not has_band_pricing:
                    form.add_error('tax_percentage_rate', 'Please Specify a Unit Rate')
                if form.cleaned_data.get('tax_percentage_rate_application_method') is None and not has_band_pricing:
                    form.add_error('tax_percentage_rate_application_method', 'Please Specify an Application Method')

            cleaned_data_copy = form.cleaned_data.copy()

            if has_band_pricing:
                if form.cleaned_data.get('band_1_type') is None and instances_of_band_1 != 0:
                    form.add_error('band_1_type', 'Please Specifiy a Condition Type')

                if form.cleaned_data.get('band_2_type') is None and instances_of_band_2 != 0:
                    form.add_error('band_2_type', 'Please Specifiy a Condition Type')

                if form.cleaned_data.get('band_1_type') is None and form.cleaned_data.get('band_2_type') is None:
                    form.add_error('band_1_type', 'Missing Condition Details')
                    for field, value in cleaned_data_copy.items():
                        if 'band_1_start' in field and value is None or 'band_1_end' in field and value is None:
                            form.add_error(field, '')

                if form.cleaned_data.get('band_1_type') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band_1', 'decimal')

                if form.cleaned_data.get('band_2_type') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band_2', 'decimal')

                for field, value in cleaned_data_copy.items():
                    if 'band_pricing' in field and value is None:
                        form.add_error(field, '')

                if charging_method == 'Percentage':
                    for field, value in cleaned_data_copy.items():
                        if 'band_method' in field and value is None:
                            form.add_error(field, '')

            if form.cleaned_data.get('taxed_by_vat'):
                taxable_tax = form.cleaned_data.get('taxable_tax')
                if not taxable_tax:
                    form.add_error('taxable_tax', f'Please select a VAT that applies to the current tax')
                    return

                has_mismatch = crosscheck_with_taxable_taxes(form, has_band_pricing,
                                                             instances_of_band_1, instances_of_band_2,
                                                             taxable_tax, 'official', form_number)

                # Django removes the k/v pair from form.cleaned_data so we can't proceed and also stacking errors
                # would confuse the user
                if has_mismatch:
                    return

            if not form.errors:
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
                specific_airport = form.cleaned_data.get('specific_airport')
                specific_region = self.tax_form_data.get('applicable_region')

                if form.cleaned_data.get('valid_ufn'):
                    valid_to = date(9999,12,31)
                    valid_ufn = True
                else:
                    valid_to = form.cleaned_data.get('valid_to')
                    valid_ufn = False

                if not self.tax_form_data.get('category'):
                    category_query = Tax.objects.get(pk = self.tax_form_data.get('tax_instance')).category_id
                else:
                    category_query = self.data.get('category')

                # Get all relevant rules, if any core properties mismatch, then we don't have an overlap
                flat_rules = TaxRule.objects.filter(Q(tax__applicable_country = self.country),
                                                    Q(tax__category_id = category_query),
                                                    Q(applies_to_private = applies_to_private) |
                                                    Q(applies_to_commercial = applies_to_commercial),
                                                    Q(applies_to_fuel = applies_to_fuel) |
                                                    Q(applies_to_fees = applies_to_fees),
                                                    Q(waived_for_tech_stop = tech_stop),
                                                    Q(pax_must_stay_aboard = pax_stays),
                                                    Q(valid_from__lte = valid_to),
                                                    Q(valid_to__gte = valid_from) | Q(valid_ufn = True))\
                                                .exclude(~Q(parent_entry = None))

                percent_rules = TaxRule.objects.filter(Q(tax_rate_percentage__tax__applicable_country = self.country),
                                                    Q(tax_rate_percentage__tax__category_id = category_query),
                                                    Q(applies_to_private = applies_to_private) |
                                                    Q(applies_to_commercial = applies_to_commercial),
                                                    Q(applies_to_fuel = applies_to_fuel) |
                                                    Q(applies_to_fees = applies_to_fees),
                                                    Q(waived_for_tech_stop = tech_stop),
                                                    Q(pax_must_stay_aboard = pax_stays),
                                                    Q(valid_from__lte = valid_to),
                                                    Q(valid_to__gte = valid_from) | Q(valid_ufn = True))\
                                                .exclude(~Q(parent_entry = None))

                if self.instance is not None:
                    flat_rules = flat_rules.exclude(id = self.instance.pk)
                    percent_rules = percent_rules.exclude(id = self.instance.pk)

                if self.type == 'airport':
                    flat_rules = flat_rules.filter(specific_airport=specific_airport)
                    percent_rules = percent_rules.filter(specific_airport=specific_airport)

                elif self.type == 'regional':

                    if not specific_region:
                        region_query = Tax.objects.get(pk = self.data.get('tax_instance')).applicable_region
                    else:
                        region_query = specific_region

                    flat_rules = flat_rules.filter(tax__applicable_region=region_query)
                    percent_rules = percent_rules.filter(tax_rate_percentage__tax__applicable_region=region_query)

                else:
                    flat_rules = flat_rules.filter(specific_airport__isnull = True,
                                                   tax_rate_percentage__tax__applicable_region__isnull = True)
                    percent_rules = percent_rules.filter(specific_airport__isnull = True,
                                                         tax__applicable_region__isnull = True)

                if charging_method == 'Percentage':
                    if percent_rules.exists():
                        for rule in percent_rules:
                            # Check if certain properties can solve the overlap
                            check_overlap_with_existing_taxes(form, rule, form.cleaned_data, valid_ufn, 'official')

                else:
                    if flat_rules.exists():
                        for rule in flat_rules:
                            check_overlap_with_existing_taxes(form, rule, form.cleaned_data, valid_ufn, 'official')

            if not form.errors and hasattr(self.instance, 'pk'):
                # Check if editing would make related taxed! official taxes and supplier defined taxes invalid
                # Current entries: the current ones are actively managed/kept an eye on, so their relation are managed
                # Past/archived entries: we no longer care about them, but we need to duplicate the current entry for
                # historical accuracy

                # Active ones
                official_taxed_taxes = TaxRule.objects.filter(Q(taxable_tax = self.instance), Q(parent_entry=None),
                                                              Q(deleted_at__isnull = True),
                                                              Q(valid_to__gte = date.today()) | Q(valid_ufn = True))

                # Inactive ones (expired, archived)
                past_official_taxed_taxes = TaxRule.objects.filter(Q(taxable_tax = self.instance), Q(parent_entry=None),
                                                              Q(valid_to__lt = date.today()) | Q(deleted_at__isnull = False))

                # Including existing, but deleted ones as well (accuracy even for deleted ones?)
                existing_taxed_exceptions = TaxRuleException.objects.filter(taxable_tax=self.instance,
                                                                            parent_entry=None,valid_ufn=True)

                past_taxed_exceptions = TaxRuleException.objects.filter(taxable_tax=self.instance,
                                                                        parent_entry=None, valid_ufn=False)

                reassign_taxes, changes_official_taxes = crosscheck_with_existing_children(form,
                                                            official_taxed_taxes, has_band_pricing,
                                                            instances_of_band_1, instances_of_band_2,
                                                            'official', form_number, 'existing', 'Edit')

                changes_past_official_taxes = crosscheck_with_existing_children(form,
                                                            past_official_taxed_taxes, has_band_pricing,
                                                            instances_of_band_1, instances_of_band_2,
                                                            'official', form_number, 'historical', 'Edit')[1]


                reassign_exceptions, changes_existing_exceptions = crosscheck_with_existing_children(form,
                                                            existing_taxed_exceptions, has_band_pricing,
                                                            instances_of_band_1, instances_of_band_2,
                                                            'exception', form_number, 'existing', 'Edit')

                changes_past_exceptions = crosscheck_with_existing_children(form,
                                                            past_taxed_exceptions, has_band_pricing,
                                                            instances_of_band_1, instances_of_band_2,
                                                            'exception', form_number, 'historical', 'Edit')[1]

                # For these two we don't need to duplicate, I think if someone modifies an existing tax, then it is for
                # a reason and current entries are managed anyway
                if changes_official_taxes:
                    if form.cleaned_data.get('confirm_checkbox'):
                        for entry in changes_official_taxes:
                            entry.taxable_tax = None
                            child_entries = entry.child_entries.all()
                            for child_entry in child_entries:
                                child_entry.taxable_tax = None
                                child_entry.save()
                            entry.save()
                    else:
                        form.cleaned_data['official_entity_id_list'] = changes_official_taxes
                        form.add_error('confirm_checkbox', '')

                if changes_existing_exceptions:
                    if form.cleaned_data.get('confirm_checkbox'):
                        for entry in changes_existing_exceptions:
                            entry.taxable_tax = None
                            child_entries = entry.child_entries.all()
                            for child_entry in child_entries:
                                child_entry.taxable_tax = None
                                child_entry.save()
                            entry.save()
                    else:
                        form.cleaned_data['exception_entity_id_list'] = changes_existing_exceptions
                        form.add_error('confirm_checkbox', '')

                # We need to duplicate the current entry for these two cases for historical accuracy
                if changes_past_exceptions or changes_past_official_taxes:
                    valid_to = form.cleaned_data.get('valid_to')

                    # Reassign, when "soft" properties like the percentage or method is changed
                    # Only prompt the below two when it is duplicated
                    if reassign_taxes:
                        for entry in reassign_taxes:
                            if entry in changes_official_taxes:
                                reassign_taxes.remove(entry)

                        form.cleaned_data['reassign_taxes'] = reassign_taxes

                    if reassign_exceptions:
                        for entry in reassign_exceptions:
                            if entry in changes_existing_exceptions:
                                reassign_exceptions.remove(entry)

                        form.cleaned_data['reassign_exceptions'] = reassign_exceptions

                    if not form.cleaned_data.get('new_valid_to_date') and form.cleaned_data.get('confirm_checkbox') and \
                        valid_to and date.today() > valid_to:
                        form.add_error('valid_to', 'Please specify a new Valid To Date in the future')

                if changes_past_exceptions:
                    form.cleaned_data['past_exception_entity_id_list'] = changes_past_exceptions
                    if not form.cleaned_data.get('confirm_checkbox'):
                        form.add_error('confirm_checkbox', '')

                if changes_past_official_taxes:
                    form.cleaned_data['past_official_entity_id_list'] = changes_past_official_taxes
                    if not form.cleaned_data.get('confirm_checkbox'):
                        form.add_error('confirm_checkbox', '')

                # Return and display a modal for confirmation

        self.validate_unique()

NewTaxRuleFormset = modelformset_factory(TaxRule,
            extra=1,
            form=TaxRuleForm,
            formset=BaseTaxRuleFormSet
            )

TaxRuleFormset = modelformset_factory(TaxRule,
            extra=0,
            form=TaxRuleForm,
            formset=BaseTaxRuleFormSet
            )

class ArchivalForm(BSModalForm):

    valid_to = forms.DateField(
        required=True,
        label='Please enter a Deletion Date',
        widget=widgets.DateInput(attrs={
            'class': 'form-control',
            'placeholder': 'YYYY-MM-DD'})
    )

    set_today = forms.BooleanField(
        required=False,
        label='Set Date Today',
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input d-block'
        })
    )

    class Meta:
        fields = ['valid_to', 'set_today']
