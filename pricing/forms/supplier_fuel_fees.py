import re
from copy import deepcopy
from datetime import time
from itertools import groupby
from django import forms
from django.db.models import Q
from django.forms import widgets
from organisation.form_widgets import OrganisationPickWidget
from organisation.models.organisation import Organisation
from core.models import HookupMethod, UnitOfMeasurement
from django_select2 import forms as s2forms
from django.forms import BaseModelFormSet, modelformset_factory
from core.models import ApronType, FuelType, PricingUnit
from core.form_widgets import HookupMethodPickWidget
from pricing.form_widgets import ApronTypePickWidget, FuelFeeCategoryPickWidget, FuelFeeUomPickWidget, HandlerPickWidget
from pricing.models import FuelFeeCategory, FuelPricingMarket, SupplierFuelFee, SupplierFuelFeeRate, \
    SupplierFuelFeeRateValidityPeriod
from ..utils.tax import validate_band_rows
from ..fields import CustomModelChoiceField
from ..form_widgets import IpaOrganisationPickCreateWidget
from ..utils.fuel_pricing_market import normalize_fraction


# Same as for the Fuel Pricing
class SupplierFeeRateForm(forms.ModelForm):
    no_change = forms.BooleanField(initial=False, required=False,
                                   widget=widgets.CheckboxInput(attrs={
                                       'class': 'form-check-input d-block no-change checkbox-align'
                                   })
                                   )

    pricing_native_amount_old = forms.DecimalField(required=False,
                                                   widget=widgets.NumberInput(attrs={
                                                       'class': 'form-control set-width',
                                                       'disabled': 'disabled'
                                                   })
                                                   )

    band_pricing_native_amount = forms.DecimalField(required=False,
                                                    widget=widgets.NumberInput(attrs={
                                                        'step': 0.000001,
                                                        'class': 'form-control auto-round-to-step'}))

    specific_hookup_method = forms.ModelChoiceField(
        empty_label='All',
        label='Hookup Method',
        queryset=HookupMethod.objects.all(),
        widget=HookupMethodPickWidget(attrs={
            'class': 'form-control',
        })
    )

    # Validity period fields

    is_local = SupplierFuelFeeRateValidityPeriod.is_local.field.formfield(
        label="Time Type",
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100 form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Local',
                'data-off': 'UTC',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }
        )
    )

    valid_from_dow = SupplierFuelFeeRateValidityPeriod.valid_from_dow.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={
                'class': 'form-control extend-label',
                'data-placeholder': 'Valid From DOW'
            },
        )
    )

    valid_to_dow = SupplierFuelFeeRateValidityPeriod.valid_to_dow.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={
                'class': 'form-control extend-label',
                'data-placeholder': 'Valid To DOW'
            },
        )
    )

    valid_from_time = SupplierFuelFeeRateValidityPeriod.valid_from_time.field.formfield(
        required=False,
        label="Valid From",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control timepicker extend-label',
            })
    )

    valid_to_time = SupplierFuelFeeRateValidityPeriod.valid_to_time.field.formfield(
        required=False,
        label="Valid To",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control timepicker extend-label',
            })
    )

    valid_all_day = forms.BooleanField(
        required=False,
        label="All Day?",
        widget=forms.CheckboxInput(
            attrs={'class': 'd-block form-check-input mt-2 extend-label'}
        )
    )

    valid_from_dow.group = 'period-row'
    valid_to_dow.group = 'period-row'
    valid_from_time.group = 'period-row'
    valid_to_time.group = 'period-row'
    valid_all_day.group = 'period-row'

    def __init__(self, *args, **kwargs):
        self.doc_instance = kwargs.pop('doc_instance', None)
        self.new_doc_instance = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Edit':
            formatted_pricing = normalize_fraction(self.instance.pricing_native_amount)

            if self.instance.quantity_band_start is not None or self.instance.weight_band_start is not None:
                self.fields['band_pricing_native_amount'].initial = formatted_pricing
        elif self.context == 'Supersede':
            # Disable hookup method field for over-wing categories
            if self.instance.supplier_fuel_fee.fuel_fee_category.applies_to_overwing_only:
                self.fields['specific_hookup_method'].disabled = True

        self.fields['delivery_method'].required = True
        self.fields['supplier_fuel_fee'].required = False
        self.fields['valid_to_date'].required = False
        self.fields['specific_fuel'].required = True
        self.fields['specific_handler_is_excluded'].required = False
        self.fields['specific_handler_is_excluded'].label = self.specific_handler_toggle_label()

        for field in self.fields:
            if 'band' in field:
                self.fields[field].required = False

        self.fields['pricing_native_unit'].label_from_instance = self.pricing_native_unit_label_from_instance
        self.fields['pricing_converted_unit'].label_from_instance = self.pricing_native_unit_label_from_instance

        delivery_qs = self.fields['delivery_method'].queryset
        self.fields['delivery_method'].queryset = delivery_qs.order_by('name')
        self.fields['delivery_method'].empty_label = 'All'

        self.fields['specific_fuel'].queryset = FuelType.objects.with_custom_ordering()
        self.fields['specific_fuel'].empty_label = 'All'

        self.fields['quantity_band_uom'].queryset = UnitOfMeasurement.objects.fluid_with_custom_ordering()
        self.fields['quantity_band_uom'].label_from_instance = self.band_unit_label_from_instance

    @staticmethod
    def pricing_native_unit_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def band_unit_label_from_instance(obj):
        return f'{obj.description_plural}'

    @staticmethod
    def specific_handler_toggle_label():
        return 'Spec. Handler is Excluded <i class ="ms-1 fa fa-info-circle" data-bs-toggle="tooltip"' \
               'data-bs-placement="top" data-bs-original-title="If the Specific Handler is set to \'excluded\',' \
               ' this fee will apply to all handlers EXCEPT the specified handler."></i>'

    class Meta:
        model = SupplierFuelFeeRate
        fields = ['supplier_fuel_fee', 'specific_fuel', 'delivery_method', 'flight_type', 'destination_type',
                  'quantity_band_start', 'quantity_band_end', 'quantity_band_uom', 'weight_band', 'weight_band_start',
                  'weight_band_end', 'pricing_native_unit', 'pricing_native_amount',
                  'no_change', 'band_pricing_native_amount', 'supplier_exchange_rate',
                  'pricing_converted_unit', 'pricing_converted_amount', 'pricing_native_amount_old',
                  'valid_from_date', 'valid_to_date', 'applies_to_commercial', 'applies_to_private',
                  'specific_handler', 'specific_handler_is_excluded', 'specific_apron', 'is_local', 'valid_from_dow',
                  'valid_to_dow', 'valid_from_time', 'valid_to_time', 'valid_all_day', 'specific_hookup_method']

        widgets = {
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'specific_fuel': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'delivery_method': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'flight_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Type'
            }),
            'destination_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Destination',
            }),
            'quantity_band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'quantity_band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'weight_band': s2forms.Select2Widget(attrs={
                'class': 'form-control set-width',
                'data-placeholder': 'Select Weight Band Type'
            }),
            'weight_band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'weight_band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'quantity_band_uom': s2forms.Select2Widget(attrs={
                'class': 'form-control set-width',
                'data-placeholder': 'Select Quantity Band Type',
            }),
            'pricing_native_unit': FuelFeeUomPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Native Pricing Unit'
            }),
            'pricing_native_amount': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
                'placeholder': ' '
            }),
            'supplier_exchange_rate': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step'
            }),
            'pricing_converted_unit': FuelFeeUomPickWidget(attrs={
                'class': 'form-control'
            }),
            'pricing_converted_amount': widgets.NumberInput(attrs={
                'class': 'form-control'
            }),
            'valid_from_date': widgets.DateInput(attrs={
                'class': 'form-control table-date-input',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD'
            }),
            'valid_to_date': widgets.DateInput(attrs={
                'class': 'form-control table-date-input',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD'
            }),
            'specific_handler': HandlerPickWidget(attrs={
                'class': 'form-control',
            }),
            'specific_handler_is_excluded': widgets.CheckboxInput(attrs={
                'class': 'd-block form-field-w-100 form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
            'specific_apron': ApronTypePickWidget(attrs={
                'class': 'form-control',
            }),
        }

    def clean(self):
        # Skip mandatory fields that have blank defaults
        if self.cleaned_data.get('specific_hookup_method') is None:
            self.errors.pop('specific_hookup_method', None)

        # Supplier XR Conversion validation
        native_uom = self.cleaned_data.get('pricing_native_unit')
        converted_uom = self.cleaned_data.get('pricing_converted_unit')

        if native_uom and converted_uom:
            # Fixed rates can only be converted into fixed rates
            if native_uom.uom.is_fluid_uom != converted_uom.uom.is_fluid_uom:
                self.add_error('pricing_converted_unit', 'Fixed and unit rates cannot be converted between.')

            # Volume to mass and vice versa conversions are impossible if no specific fuel selected
            if not self.has_error('pricing_converted_unit') and not self.cleaned_data.get('specific_fuel', None):
                if any([native_uom.uom.is_volume_uom != converted_uom.uom.is_volume_uom,
                        native_uom.uom.is_mass_uom != converted_uom.uom.is_mass_uom]):
                    self.add_error('pricing_converted_unit', 'Mass and volume unit rates can only be converted between'
                                                             ' if the fee applies to a specific fuel type.')

        # Validity Period validation
        dow_names = SupplierFuelFeeRateValidityPeriod.DOW_SHORT_NAMES
        period_rows = groupby({k: v for k, v in self.fields.items()
                               if 'period-row' in getattr(v, 'group', '')}.items(),
                              lambda item: item[1].group)
        period_dicts = []

        for _, row_fields in period_rows:
            field_names = {}
            field_values = {}

            for name, _ in row_fields:
                name_root = re.sub(r'-additional-\d+', '', name)
                field_names[name_root] = name
                field_values[name_root] = self.cleaned_data[name]

            # Empty rows are OK
            if all([not v for v in field_values.values()]):
                continue

            # Check for partially empty rows
            period_complete = True

            if not field_values['valid_from_dow']:
                self.add_error(field_names['valid_from_dow'], "DOW is required")
                period_complete = False

            if not field_values['valid_to_dow']:
                self.add_error(field_names['valid_to_dow'], "DOW is required")
                period_complete = False

            if not field_values['valid_all_day']:
                if not field_values['valid_from_time']:
                    self.add_error(field_names['valid_from_time'], "Time is required")
                    period_complete = False

                if not field_values['valid_to_time']:
                    self.add_error(field_names['valid_to_time'], "Time is required")
                    period_complete = False
            else:
                field_values['valid_from_time'] = time(0, 0, 0)
                field_values['valid_to_time'] = time(23, 59, 59)

            # Check if period has positive length (at least 1 minute and end dow >= start dow)
            if period_complete:
                period_valid = True

                if field_values['valid_from_dow'] > field_values['valid_to_dow']:
                    self.add_error(field_names['valid_to_dow'], "Valid To DOW cannot be earlier than"
                                                                " Valid From DOW")
                    period_valid = False
                if field_values['valid_from_time'] >= field_values['valid_to_time']:
                    self.add_error(field_names['valid_to_time'], "Valid To Time must be later than"
                                                                 " Valid From Time")
                    period_valid = False

                if period_valid:
                    # Cross-check with previous periods for overlap
                    for prev_period in period_dicts:
                        days_overlap = field_values['valid_from_dow'] <= prev_period['valid_to_dow'] \
                                       and field_values['valid_to_dow'] >= prev_period['valid_from_dow']

                        time_overlap = field_values['valid_from_time'] <= prev_period['valid_to_time'] \
                                       and field_values['valid_to_time'] >= prev_period['valid_from_time']

                        if days_overlap and time_overlap:
                            self.add_error(field_names['valid_from_dow'],
                                           f"This period overlaps with one of the previous periods"
                                           f" ({dow_names[prev_period['valid_from_dow']]}"
                                           f" - {dow_names[prev_period['valid_to_dow']]},"
                                           f" {prev_period['valid_from_time'].strftime('%H:%M')}"
                                           f" - {prev_period['valid_to_time'].strftime('%H:%M')})")
                            break

                    period_dicts.append(field_values)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field == '__all__':
                continue

            if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs[
                'class']:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
            elif 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid


class BaseFuelFeeRateFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('doc_instance', None)
        self.new_document = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.extra_period_fields = kwargs.pop('extra_period_fields', None)
        self.entry = kwargs.pop('entry', None)
        self.related_entries = kwargs.pop('related_entries', None)
        self.existing_periods = kwargs.pop('existing_periods', None)
        self.fee_formset = kwargs.pop('fee_formset', None)
        self.single_fee_pk = kwargs.pop('single_fee_pk', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Edit':
            self.queryset = self.entry

        elif self.context == 'Supersede':
            if self.document_type == 'agreement':
                locations = self.document.all_pricing_location_pks

                self.all_entries = SupplierFuelFeeRate.objects \
                    .filter(deleted_at__isnull=True,
                            supplier_fuel_fee__supplier=self.document.supplier,
                            supplier_fuel_fee__location__in=locations,
                            source_agreement=self.document)
            else:
                locations = self.document.pld_at_location.all().values('location')

                self.all_entries = SupplierFuelFeeRate.objects \
                    .filter(price_active=True,
                            deleted_at__isnull=True,
                            supplier_fuel_fee__supplier=self.document.supplier,
                            supplier_fuel_fee__location__in=locations,
                            supplier_fuel_fee__related_pld=self.document)

            if self.single_fee_pk:
                # For superseding of individual fees within same document
                self.queryset = self.all_entries.filter(pk=self.single_fee_pk)
            else:
                self.queryset = self.all_entries.order_by(
                    'supplier_fuel_fee', 'quantity_band_start','weight_band_start').distinct('supplier_fuel_fee')

            for form in self.forms:
                form.empty_permitted = False
                # On form errors, we lose the instance, but I still want to display the old price
                form['pricing_native_amount_old'].initial = normalize_fraction(form['pricing_native_amount'].initial)
                form['pricing_native_amount'].initial = ''
                form['valid_from_date'].initial = ''

        # Creation
        else:
            self.queryset = SupplierFuelFeeRate.objects.none()

            self.forms[0].empty_permitted = False

        for value, form in enumerate(self.forms):
            form['quantity_band_start'].initial = normalize_fraction(form['quantity_band_start'].initial)
            form['quantity_band_end'].initial = normalize_fraction(form['quantity_band_end'].initial)
            form['weight_band_start'].initial = normalize_fraction(form['weight_band_start'].initial)
            form['weight_band_end'].initial = normalize_fraction(form['weight_band_end'].initial)

            if self.context != 'Supersede':
                form['pricing_native_amount'].initial = normalize_fraction(form['pricing_native_amount'].initial)

        context_prefixes = {
            'Create': 'new-fuel-fee-rate',
            'Edit': 'fuel-fee',
            'Supersede': 'existing-fuel-fee-rate',
        }
        prefix = context_prefixes[self.context]

        for value, form in enumerate(self.forms):
            if self.context != 'Supersede':
                # Register dependent fields
                form.fields['specific_handler'].widget = HandlerPickWidget(
                    queryset=Organisation.objects.handling_agent(),
                    dependent_fields={
                        f'{prefix}-{value}-location': 'handler_details__airport'},
                    attrs={'class': 'form-control'}
                )
            else:
                # No dependent field needed, but need to update queryset for each field
                form.fields['specific_handler'].widget = HandlerPickWidget(
                    queryset=Organisation.objects.handling_agent().filter(
                        handler_details__airport=form.instance.supplier_fuel_fee.location
                    ),
                    attrs={'class': 'form-control'}
                )

    def add_fields(self, form, index):
        super(BaseFuelFeeRateFormSet, self).add_fields(form, index)

        if self.context == 'Supersede':
            classes = 'form-control band-width'
        else:
            classes = 'form-control'

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'quantity_band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        form.fields[f'quantity_band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        form.fields[f'weight_band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        form.fields[f'weight_band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        if self.context == 'Supersede':
                            related_entries = SupplierFuelFeeRate.objects.filter(
                                supplier_fuel_fee_id=form['supplier_fuel_fee'].initial) \
                                                  .order_by('quantity_band_start', 'weight_band_start')[1:]

                            if value < related_entries.count():
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                       widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                                         'disabled': 'disabled'}))
                            else:
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                       widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                                         'disabled': 'disabled'}))

                        form.fields[f'band_pricing_native_amount-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                               widget=widgets.NumberInput(
                                                   attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

        elif self.related_entries or self.context == 'Supersede':
            related_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee_id=form['supplier_fuel_fee'].initial) \
                                  .order_by('quantity_band_start', 'weight_band_start')[1:]
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'quantity_band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.quantity_band_start),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step'}))

                form.fields[f'quantity_band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.quantity_band_end),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step'}))

                form.fields[f'weight_band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.weight_band_start),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step'}))

                form.fields[f'weight_band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.weight_band_end),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step'}))

                if self.context == 'Supersede':
                    form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(entry.pricing_native_amount),
                                           widget=widgets.NumberInput(
                                               attrs={'step': 0.0001, 'class': 'form-control', 'disabled': 'disabled'}))

                form.fields[f'band_pricing_native_amount-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(
                        entry.pricing_native_amount) if self.context != 'Supersede' else '',
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': 'form-control auto-round-to-step'}))

        # ADD/POPULATE VALIDITY PERIOD FIELDS
        additional_row_count = 0
        validity_period_row_fields = {
            'valid_from_dow': 'col-md-3 mb-3',
            'valid_to_dow': 'col-md-3 mb-3',
            'valid_from_time': 'col-md-2 mb-3',
            'valid_to_time': 'col-md-2 mb-3',
            'valid_all_day': 'col-md-1 mb-3'
        }

        existing_periods = self.existing_periods if self.context == 'Edit' \
            else form.instance.validity_periods_sorted

        # Get additional field count and load first row's data on GET
        if existing_periods:
            additional_row_count = len(existing_periods) - 1

            form.fields[f'is_local'].initial = existing_periods[0].is_local
            form.fields[f'valid_from_dow'].initial = existing_periods[0].valid_from_dow
            form.fields[f'valid_to_dow'].initial = existing_periods[0].valid_to_dow
            form.fields[f'valid_from_time'].initial = existing_periods[0].valid_from_time.strftime("%H:%M")
            form.fields[f'valid_to_time'].initial = existing_periods[0].valid_to_time.strftime("%H:%M")
            form.fields[f'valid_all_day'].initial = existing_periods[0].valid_all_day

        # Get additional field count on POST
        elif self.extra_period_fields:
            additional_row_count = self.extra_period_fields[index]

        # Prepare and populate additional period rows
        for value in range(0, int(additional_row_count)):
            for field_name, wrapper_classes in validity_period_row_fields.items():
                form.fields[f'{field_name}-additional-{value + 1}'] = deepcopy(form.fields[field_name])
                form.fields[f'{field_name}-additional-{value + 1}'].group = f'additional-period-row-{value + 1}'
                form.fields[f'{field_name}-additional-{value + 1}'].wrapper_classes = wrapper_classes

                if existing_periods:
                    field_value = getattr(existing_periods[value + 1], field_name)

                    if isinstance(field_value, time):
                        field_value = field_value.strftime("%H:%M")

                    form.fields[f'{field_name}-additional-{value + 1}'].initial = field_value

    def clean(self):
        for form_number, form in enumerate(self.forms):
            cleaned_data_copy = form.cleaned_data.copy()

            if form.cleaned_data.get('delivery_method') is None:
                form.errors.pop('delivery_method', None)

            if form.cleaned_data.get('specific_fuel') is None:
                form.errors.pop('specific_fuel', None)

            if form.cleaned_data.get('pricing_native_amount') is None and form.cleaned_data.get(
                'band_pricing_native_amount') is not None:
                for error in list(form.errors):
                    if 'pricing_native_amount' in error:
                        del form._errors['pricing_native_amount']
                        break

            # Get the data from related Fee Formset
            if self.fee_formset:
                fee_formset_data = self.fee_formset[form_number].cleaned_data

                # Validate if hookup method is set correctly for fees where category applies to over-wing only
                category = fee_formset_data.get('fuel_fee_category')
                hookup_method = form.cleaned_data.get('specific_hookup_method')

                if getattr(category, 'applies_to_overwing_only', None) and getattr(hookup_method, 'code', None) != 'OW':
                    form.add_error('specific_hookup_method', "Fees in categories applying only to over-wing fuelling"
                                                             " cannot apply to other hookup methods.")

                if form.cleaned_data.get('pricing_native_unit') and form.cleaned_data.get('fuel_fee_category'):
                    if form.cleaned_data['pricing_native_unit'].uom.is_fluid_uom:
                        if fee_formset_data['fuel_fee_category'].applies_for_no_fuel_uplift:
                            form.add_error('pricing_native_unit', "Fees applicable when no fuel is uplifted cannot be"
                                                                  " defined in terms of fuel uplift quantity.")
                        elif fee_formset_data['fuel_fee_category'].applies_for_defueling:
                            form.add_error('pricing_native_unit', "Fees applicable for defueling cannot be"
                                                                  " defined in terms of fuel uplift quantity.")

                if form.cleaned_data.get('pricing_converted_unit') and fee_formset_data.get('fuel_fee_category'):
                    if form.cleaned_data['pricing_converted_unit'].uom.is_fluid_uom:
                        if fee_formset_data['fuel_fee_category'].applies_for_no_fuel_uplift:
                            form.add_error('pricing_converted_unit', "Fees applicable when no fuel is uplifted cannot"
                                                                     " be defined in terms of fuel uplift quantity.")
                        elif fee_formset_data['fuel_fee_category'].applies_for_defueling:
                            form.add_error('pricing_converted_unit', "Fees applicable for defueling cannot be"
                                                                     " defined in terms of fuel uplift quantity.")

                # Also disallow quantity bands
                if form.cleaned_data.get('quantity_band_uom') and fee_formset_data.get('fuel_fee_category'):
                    if fee_formset_data['fuel_fee_category'].applies_for_no_fuel_uplift:
                        form.add_error('quantity_band_uom', "Fees applicable when no fuel is uplifted cannot"
                                                            " be defined with fuel uplift quantity bands.")

                    if fee_formset_data['fuel_fee_category'].applies_for_defueling:
                        form.add_error('quantity_band_uom', "Fees applicable for defueling cannot be"
                                                            " be defined with fuel uplift quantity bands.")

            if form.cleaned_data.get('no_change'):
                form._errors.pop('valid_from_date', None)

            if form.cleaned_data.get('DELETE'):
                if form.cleaned_data.get('valid_to_date') is None:
                    form.add_error('valid_to_date', 'Please specify a fee expiration date')
                    # For some reason, without error raising, the form just skips validation
                    raise forms.ValidationError("Expiration date is required")
                else:
                    for error in list(form.errors):
                        del form._errors[error]

            if self.context == 'Supersede' and not form.cleaned_data.get('no_change'):
                valid_from = form.cleaned_data.get('valid_from_date')
                if not valid_from:
                    form.add_error('valid_from_date', f'')
                elif form.cleaned_data.get('valid_from_date') < form.cleaned_data.get('id').valid_from_date:
                    form.add_error('valid_from_date',
                                   f'Needs to be later than {form.cleaned_data.get("id").valid_from_date}')

            instances_of_band_1 = 0
            instances_of_band_2 = 0

            has_band_pricing = False
            for field, value in form.cleaned_data.items():
                if 'quantity_band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_1 += 1
                if 'weight_band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_2 += 1

            if has_band_pricing:
                # Earlier validation fail makes the quantity_band_uom value in cleaned_data None
                if not form.errors.get('quantity_band_uom'):
                    if form.cleaned_data.get('quantity_band_uom') is None and instances_of_band_1 != 0:
                        form.add_error('quantity_band_uom', 'Please Specify a Quantity Band')

                if form.cleaned_data.get('weight_band') is None and instances_of_band_2 != 0:
                    form.add_error('band_2_type', 'Please Specify a Weight Band')

                if form.cleaned_data.get('quantity_band_uom') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'quantity_band', 'integer')

                if form.cleaned_data.get('weight_band') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'weight_band', 'integer')

                for field, value in form.cleaned_data.items():
                    if self.context == 'Supersede':
                        if 'band_pricing_native_amount-additional' in field and value is None:
                            form.add_error(field, '')
                    else:
                        if 'band_pricing' in field and value is None:
                            form.add_error(field, '')

            if form.has_changed():
                data = form.cleaned_data
                if not data.get('applies_to_private') and not data.get('applies_to_commercial'):
                    form.add_error('applies_to_private', 'One of the checkboxes needs to be checked')
                    form.add_error('applies_to_commercial', '')

                if self.document_type == 'agreement':
                    doc_for_date = self.new_document if self.context == 'Supersede' else self.document

                    if (data.get('valid_from_date') and doc_for_date.end_date
                        and data.get('valid_from_date') > doc_for_date.end_date.date()):
                        form.add_error('valid_from_date',
                                       f'The valid from date cannot be later than the end date of'
                                       f' the agreement ({doc_for_date.end_date.strftime("%Y-%m-%d")})')

        self.validate_unique()


SupplierFeeRateFormset = modelformset_factory(SupplierFuelFeeRate,
                                              can_delete=True,
                                              extra=0,
                                              form=SupplierFeeRateForm,
                                              formset=BaseFuelFeeRateFormSet
                                              )

NewSupplierFeeRateFormset = modelformset_factory(SupplierFuelFeeRate,
                                                 extra=10,
                                                 can_delete=True,
                                                 form=SupplierFeeRateForm,
                                                 formset=BaseFuelFeeRateFormSet
                                                 )


# Used for the same purposes as the Fuel Pricing form minus superseding
class SupplierFeesForm(forms.ModelForm):
    # A custom field is needed, because we'll get an error when we have one IPA at several locations
    custom_ipa = CustomModelChoiceField(
        required=True,
        queryset=Organisation.objects.all(),
        widget=IpaOrganisationPickCreateWidget(
            attrs={
                'class': 'form-control',
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.doc_instance = kwargs.pop('doc_instance', None)
        self.new_doc_instance = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        super().__init__(*args, **kwargs)

        self.fields['location'].initial = self.entry[0].supplier_fuel_fee.location
        self.fields['location'].disabled = True
        self.fields['location'].required = False

        self.fields['local_name'].required = True

        self.fields['supplier'].initial = self.doc_instance.supplier

        if self.document_type == 'agreement':
            self.fields['location'].queryset = Organisation.objects.filter(
                airport_details__organisation__in=self.doc_instance.pricing_formulae.all().values('location')
                .union(self.doc_instance.pricing_manual.all().values('location')))
        else:
            self.fields['location'].queryset = Organisation.objects.filter(
                airport_details__organisation__in=self.doc_instance.pld_at_location.all().values('location'))

        # Check the first IPA field against location field
        location = self.fields['location'].initial

        if location and self.document_type == 'pld':
            pricing_pks = location.fuel_pricing_market_plds_at_location \
                .filter(pld=self.doc_instance).values_list('fuel_pricing_market__pk', flat=True)
            self.fields['custom_ipa'].required = not FuelPricingMarket.objects.filter(
                Q(pk__in=pricing_pks) & Q(deleted_at__isnull=True)
                & Q(price_active=True) & Q(ipa__isnull=True)
            ).exists()
        else:
            self.fields['custom_ipa'].required = True

        self.fields['custom_ipa'].label_from_instance = self.ipa_label_from_instance
        self.fields['location'].label_from_instance = self.location_label_from_instance

        self.fields['custom_ipa'].initial = self.entry[0].supplier_fuel_fee.ipa

        self.fields['custom_ipa'].widget = IpaOrganisationPickCreateWidget(
            attrs={'data-placeholder': self.ipa_data_placeholder},
            queryset=self.get_ipa_qs(), dependent_fields={f'fuel-fee-0-location': 'ipa_locations'},
            context='formset', form_name=f'fuel-fee-0')

    @property
    def ipa_data_placeholder(self):
        if self.document_type == 'pld':
            return "TBC / Confirmed on Order"
        else:
            return "Please Select or Create an Into-Plane Agent"

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.airport_details.fullname}'

    @staticmethod
    def ipa_label_from_instance(obj):
        return f'{obj.details.registered_name}'

    @staticmethod
    def pricing_native_unit_label_from_instance(obj):
        return f'{obj.description}'

    def get_ipa_qs(self):
        if self.document_type == 'agreement':
            return Organisation.objects.filter(
                Q(ipa_locations__in=self.doc_instance.pricing_formulae.all().values('location')) |
                Q(ipa_locations__in=self.doc_instance.pricing_manual.all().values('location'))
            ).distinct()
        else:
            return Organisation.objects.filter(
                ipa_locations__in=self.doc_instance.pld_at_location.all().values('location'))

    class Meta:
        model = SupplierFuelFee
        fields = ['local_name', 'supplier', 'location', 'custom_ipa', 'fuel_fee_category']

        widgets = {
            'local_name': widgets.TextInput(attrs={
                'class': 'form-control local-name',
            }),
            # Not used in this context
            'supplier': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'location': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Location'
            }),
            'ipa': OrganisationPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Into-Plane Agent'
            }),
            'fuel_fee_category': FuelFeeCategoryPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Fee Category'
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


class BaseSupplierFuelFeeFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('doc_instance', None)
        self.new_document = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        super().__init__(*args, **kwargs)

        self.queryset = SupplierFuelFee.objects.filter(id=self.entry[0].supplier_fuel_fee_id)


SupplierFeesFormset = modelformset_factory(SupplierFuelFee,
                                           extra=0,
                                           form=SupplierFeesForm,
                                           formset=BaseSupplierFuelFeeFormSet
                                           )


# Used on Fuel Pricing Supersede to set dates for all rows
# Used on Fuel Fee Supersede to set valid from dates for all rows
class SupersedePricingDatesForm(forms.Form):
    apply_to_all = forms.BooleanField(widget=widgets.CheckboxInput(attrs={
        'class': 'header-date-open'
    }), required=False)

    valid_from = forms.DateField(widget=widgets.DateInput(attrs={
        'class': 'form-control date-input header-date-input',
        'type': 'text',
        'placeholder': 'Valid From'
    }), required=False)

    valid_to = forms.DateField(widget=widgets.DateInput(attrs={
        'class': 'form-control date-input header-date-input',
        'type': 'text',
        'placeholder': 'Valid To'}), required=False)

    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', None)
        super().__init__(*args, **kwargs)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if 'class' in self.fields[field].widget.attrs and 'is-invalid' not in self.fields[field].widget.attrs[
                'class']:
                self.fields[field].widget.attrs['class'] += ' is-invalid'
            elif 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        if self.context == 'fuel-pricing':
            if cleaned_data.get('apply_to_all') and not cleaned_data.get('valid_from') and not cleaned_data.get(
                'valid_to'):
                self.add_error('valid_from', 'This field is required.')
                self.add_error('valid_to', 'This field is required.')
        else:
            if cleaned_data.get('apply_to_all') and not cleaned_data.get('valid_from'):
                self.add_error('valid_to', 'This field is required')
        return cleaned_data


####################
# NEW COMBINED FORMS
####################


# Only for creating (for now)
class CombinedFuelFeeForm(forms.ModelForm):
    band_pricing_native_amount = forms.DecimalField(required=False,
                                                    widget=widgets.NumberInput(attrs={
                                                        'step': 0.000001,
                                                        'class': 'form-control auto-round-to-step'}))

    # Combined Form - fields
    local_name = SupplierFuelFee.local_name.field.formfield(
        required=True,
        widget=widgets.TextInput(
            attrs={'class': 'form-control'}
        )
    )

    location = SupplierFuelFee.location.field.formfield(
        required=True,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select an Airport'}
        )
    )

    ipa = SupplierFuelFee.ipa.field.formfield(
        required=False,
        widget=OrganisationPickWidget(
            attrs={'class': 'form-control'}
        )
    )

    fuel_fee_category = SupplierFuelFee.fuel_fee_category.field.formfield(
        required=True,
        queryset=FuelFeeCategory.objects.all(),
        widget=FuelFeeCategoryPickWidget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select a Category'}
        )
    )

    # Validity period fields

    is_local = SupplierFuelFeeRateValidityPeriod.is_local.field.formfield(
        label="Time Type",
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100 form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Local',
                'data-off': 'UTC',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }
        )
    )

    valid_from_dow = SupplierFuelFeeRateValidityPeriod.valid_from_dow.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control extend-label'})
    )

    valid_to_dow = SupplierFuelFeeRateValidityPeriod.valid_to_dow.field.formfield(
        required=False,
        widget=s2forms.Select2Widget(
            attrs={'class': 'form-control extend-label'})
    )

    valid_from_time = SupplierFuelFeeRateValidityPeriod.valid_from_time.field.formfield(
        required=False,
        label="Valid From",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control timepicker extend-label',
            })
    )

    valid_to_time = SupplierFuelFeeRateValidityPeriod.valid_to_time.field.formfield(
        required=False,
        label="Valid To",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control timepicker extend-label',
            })
    )

    valid_all_day = forms.BooleanField(
        required=False,
        label="All Day?",
        widget=forms.CheckboxInput(
            attrs={'class': 'd-block form-check-input mt-2 extend-label'}
        )
    )

    specific_hookup_method = forms.ModelChoiceField(
        empty_label='All',
        queryset=HookupMethod.objects.all(),
        widget=HookupMethodPickWidget(attrs={
            'class': 'form-control',
        })
    )

    valid_from_dow.group = 'period-row'
    valid_to_dow.group = 'period-row'
    valid_from_time.group = 'period-row'
    valid_to_time.group = 'period-row'
    valid_all_day.group = 'period-row'

    def __init__(self, *args, **kwargs):
        self.doc_instance = kwargs.pop('doc_instance', None)
        self.new_doc_instance = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        super().__init__(*args, **kwargs)

        self.fields['supplier_fuel_fee'].required = False
        self.fields['valid_to_date'].required = False

        for field in self.fields:
            if 'band' in field:
                self.fields[field].required = False

        self.fields['pricing_native_unit'].label_from_instance = self.pricing_native_unit_label_from_instance
        self.fields['pricing_converted_unit'].label_from_instance = self.pricing_native_unit_label_from_instance

        self.fields['delivery_method'].empty_label = 'All'

        self.fields['specific_fuel'].queryset = FuelType.objects.with_custom_ordering()
        self.fields['specific_fuel'].empty_label = 'All'

        self.fields['quantity_band_uom'].queryset = UnitOfMeasurement.objects.fluid_with_custom_ordering()
        self.fields['quantity_band_uom'].label_from_instance = self.band_unit_label_from_instance

        self.fields['local_name'].required = True

        if self.document_type == 'agreement':
            self.fields['location'].queryset = Organisation.objects.filter(
                airport_details__organisation__in=self.doc_instance.pricing_formulae.all().values('location')
                .union(self.doc_instance.pricing_manual.all().values('location')))
        else:
            self.fields['location'].queryset = Organisation.objects.filter(
                airport_details__organisation__in=self.doc_instance.pld_at_location.all().values('location'))

        self.fields['location'].label_from_instance = self.location_label_from_instance

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.airport_details.fullname}'

    @staticmethod
    def pricing_native_unit_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def band_unit_label_from_instance(obj):
        return f'{obj.description_plural}'

    class Meta:
        model = SupplierFuelFeeRate
        fields = ['supplier_fuel_fee', 'specific_fuel', 'delivery_method', 'flight_type', 'destination_type',
                  'quantity_band_start', 'quantity_band_end', 'quantity_band_uom', 'weight_band', 'weight_band_start',
                  'weight_band_end', 'pricing_native_amount',
                  'band_pricing_native_amount', 'supplier_exchange_rate',
                  'pricing_converted_amount', 'pricing_converted_unit',
                  'valid_from_date', 'valid_to_date', 'pricing_native_unit', 'location', 'ipa', 'fuel_fee_category',
                  'specific_hookup_method', 'applies_to_private', 'applies_to_commercial',
                  'specific_handler', 'specific_handler_is_excluded', 'specific_apron', 'is_local', 'valid_from_dow',
                  'valid_to_dow', 'valid_from_time', 'valid_to_time', 'valid_all_day']

        widgets = {
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'specific_fuel': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'delivery_method': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            }),
            'flight_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Type'
            }),
            'destination_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Destination',
            }),
            'quantity_band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'quantity_band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'weight_band': s2forms.Select2Widget(attrs={
                'class': 'form-control set-width',
                'data-placeholder': 'Select Weight Band Type'
            }),
            'weight_band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'weight_band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'quantity_band_uom': s2forms.Select2Widget(attrs={
                'class': 'form-control set-width',
                'data-placeholder': 'Select Quantity Band Type',
            }),
            'pricing_native_unit': FuelFeeUomPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Native Pricing Unit'
            }),
            'pricing_native_amount': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step',
            }),
            'supplier_exchange_rate': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step'
            }),
            'pricing_converted_unit': FuelFeeUomPickWidget(attrs={
                'class': 'form-control'
            }),
            'pricing_converted_amount': widgets.NumberInput(attrs={
                'class': 'form-control'
            }),
            'valid_from_date': widgets.DateInput(attrs={
                'class': 'form-control table-date-input',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD'
            }),
            'valid_to_date': widgets.DateInput(attrs={
                'class': 'form-control table-date-input',
                'type': 'text',
                'placeholder': 'YYYY-MM-DD'
            }),
            'specific_handler': HandlerPickWidget(attrs={
                'class': 'form-control',
            }),
            'specific_handler_is_excluded': widgets.CheckboxInput(attrs={
                'class': 'd-block form-field-w-100 form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
            'specific_apron': ApronTypePickWidget(attrs={
                'class': 'form-control',
            }),
        }

    def clean(self):
        # Skip mandatory fields that have blank defaults
        if self.cleaned_data.get('specific_hookup_method') is None:
            self.errors.pop('specific_hookup_method', None)

        # Validate if hookup method is set correctly for fees where category applies to over-wing only
        category = self.cleaned_data.get('fuel_fee_category')
        hookup_method = self.cleaned_data.get('specific_hookup_method')

        if getattr(category, 'applies_to_overwing_only', None) and getattr(hookup_method, 'code', None) != 'OW':
            self.add_error('specific_hookup_method', "Fees in categories applying only to over-wing fuelling"
                                                     " cannot apply to other hookup methods.")

        # Validate if fluid units are not used for non-uplift fees
        for field, value in dict(self.cleaned_data).items():
            if value is None:
                continue

            if 'pricing_native_unit' in field or 'pricing_converted_unit' in field:
                if not self.cleaned_data.get('fuel_fee_category', None):
                    continue

                if value.uom.is_fluid_uom:
                    if self.cleaned_data['fuel_fee_category'].applies_for_no_fuel_uplift:
                        self.add_error(field, "Fees applicable when no fuel is uplifted cannot be"
                                              " defined in terms of fuel uplift quantity.")
                    elif self.cleaned_data['fuel_fee_category'].applies_for_defueling:
                        self.add_error(field, "Fees applicable for defueling cannot be"
                                              " defined in terms of fuel uplift quantity.")

            # Also disallow quantity bands
            if 'quantity_band_uom' in field:
                if not self.cleaned_data.get('fuel_fee_category', None):
                    continue

                if self.cleaned_data['fuel_fee_category'].applies_for_no_fuel_uplift:
                    self.add_error(field, "Fees applicable when no fuel is uplifted cannot"
                                          " be defined with fuel uplift quantity bands.")
                elif self.cleaned_data['fuel_fee_category'].applies_for_defueling:
                    self.add_error(field, "Fees applicable for defueling cannot be"
                                          " be defined with fuel uplift quantity bands.")

        # Supplier XR Conversion validation
        native_uoms = {k: self.cleaned_data.get(k) for k in self.fields
                       if 'pricing_native_unit' in k and self.cleaned_data.get(k) is not None}

        converted_uom = self.cleaned_data['pricing_converted_unit']

        # Conversion can only be applied, if all locations use the same currency
        native_currs = {c.currency for c in native_uoms.values()}

        if converted_uom and len(native_currs) > 1:
            self.add_error('pricing_converted_unit', 'Supplier currency override can only be used if all locations'
                                                     ' covered by the fee use the same currency.')

        for field_name, native_uom in native_uoms.items():
            if native_uom and converted_uom:
                # Fixed rates can only be converted into fixed rates
                if not self.has_error('pricing_converted_unit') \
                    and native_uom.uom.is_fluid_uom != converted_uom.uom.is_fluid_uom:
                    self.add_error('pricing_converted_unit', 'Fixed and unit rates cannot be converted between.')

                # Volume to mass and vice versa conversions are impossible if no specific fuel selected
                if not self.has_error('pricing_converted_unit') and not self.cleaned_data.get('specific_fuel', None):
                    if any([native_uom.uom.is_volume_uom != converted_uom.uom.is_volume_uom,
                        native_uom.uom.is_mass_uom != converted_uom.uom.is_mass_uom]):
                        self.add_error('pricing_converted_unit', 'Mass and volume unit rates can only be converted'
                                                                 ' between if the fee applies to a specific fuel type.')

        # Validity period validation
        dow_names = SupplierFuelFeeRateValidityPeriod.DOW_SHORT_NAMES
        period_rows = groupby({k: v for k, v in self.fields.items()
                               if 'period-row' in getattr(v, 'group', '')}.items(),
                              lambda item: item[1].group)
        period_dicts = []

        for _, row_fields in period_rows:
            field_names = {}
            field_values = {}

            for name, _ in row_fields:
                name_root = re.sub(r'-additional-\d+', '', name)
                field_names[name_root] = name
                field_values[name_root] = self.cleaned_data[name]

            # Empty rows are OK
            if all([not v for v in field_values.values()]):
                continue

            # Check for partially empty rows
            period_complete = True

            if not field_values['valid_from_dow']:
                self.add_error(field_names['valid_from_dow'], "DOW is required")
                period_complete = False

            if not field_values['valid_to_dow']:
                self.add_error(field_names['valid_to_dow'], "DOW is required")
                period_complete = False

            if not field_values['valid_all_day']:
                if not field_values['valid_from_time']:
                    self.add_error(field_names['valid_from_time'], "Time is required")
                    period_complete = False

                if not field_values['valid_to_time']:
                    self.add_error(field_names['valid_to_time'], "Time is required")
                    period_complete = False
            else:
                field_values['valid_from_time'] = time(0, 0, 0)
                field_values['valid_to_time'] = time(23, 59, 59)

            # Check if period has positive length (at least 1 minute and end dow >= start dow)
            if period_complete:
                period_valid = True

                if field_values['valid_from_dow'] > field_values['valid_to_dow']:
                    self.add_error(field_names['valid_to_dow'], "Valid To DOW cannot be earlier than"
                                                                " Valid From DOW")
                    period_valid = False
                if field_values['valid_from_time'] >= field_values['valid_to_time']:
                    self.add_error(field_names['valid_to_time'], "Valid To Time must be later than"
                                                                 " Valid From Time")
                    period_valid = False

                if period_valid:
                    # Cross-check with previous periods for overlap
                    for prev_period in period_dicts:
                        days_overlap = field_values['valid_from_dow'] <= prev_period['valid_to_dow'] \
                                       and field_values['valid_to_dow'] >= prev_period['valid_from_dow']

                        time_overlap = field_values['valid_from_time'] <= prev_period['valid_to_time'] \
                                       and field_values['valid_to_time'] >= prev_period['valid_from_time']

                        if days_overlap and time_overlap:
                            self.add_error(field_names['valid_from_dow'],
                                           f"This period overlaps with one of the previous periods"
                                           f" ({dow_names[prev_period['valid_from_dow']]}"
                                           f" - {dow_names[prev_period['valid_to_dow']]},"
                                           f" {prev_period['valid_from_time'].strftime('%H:%M')}"
                                           f" - {prev_period['valid_to_time'].strftime('%H:%M')})")
                            break

                    period_dicts.append(field_values)

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


# Used for creating fuel fees and rates, reason for duplication is to reduce the amount of for loops required in templates
# plus it is easier to save like this (loop through every location, create rates)
# (leaving in references to edit and supersede, as we might move use it there also)
class CombinedFuelFeeFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('doc_instance', None)
        self.new_document = kwargs.pop('new_doc_instance', None)
        self.document_type = kwargs.pop('doc_type', None)
        self.context = kwargs.pop('context', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.extra_period_fields = kwargs.pop('extra_period_fields', None)
        self.extra_location_fields = kwargs.pop('extra_location_fields', None)
        self.entry = kwargs.pop('entry', None)
        self.related_entries = kwargs.pop('related_entries', None)
        super().__init__(*args, **kwargs)

        self.queryset = SupplierFuelFeeRate.objects.none()

        ipa_qs = self.get_ipa_qs()
        handler_qs = self.get_handler_qs()

        for value, form in enumerate(self.forms):
            form.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                attrs={'data-placeholder': self.ipa_data_placeholder}, queryset=ipa_qs,
                dependent_fields={f'new-fuel-fee-rate-{value}-location': 'ipa_locations'},
                context='formset', form_name=f'new-fuel-fee-rate-{value}')

            form.fields['specific_handler'].widget = HandlerPickWidget(
                queryset=handler_qs,
                dependent_fields={
                    f'new-fuel-fee-rate-{value}-location': 'handler_details__airport'},
                attrs={'class': 'form-control'}
            )

            # Check the first IPA field against first location field
            location_pk = form.data.get(f'{self.prefix}-{value}-location') if hasattr(form, 'data') else None
            location = Organisation.objects.filter(pk=location_pk).first() if location_pk else None

            if location and self.document_type == 'pld':
                pricing_pks = location.fuel_pricing_market_plds_at_location \
                    .filter(pld=self.document).values_list('fuel_pricing_market__pk', flat=True)
                form.fields['ipa'].required = not FuelPricingMarket.objects.filter(
                    Q(pk__in=pricing_pks) & Q(deleted_at__isnull=True)
                    & Q(price_active=True) & Q(ipa__isnull=True)
                ).exists()
            else:
                form.fields['ipa'].required = True

        self.forms[0].empty_permitted = False

        for form in self.forms:
            form['quantity_band_start'].initial = normalize_fraction(form['quantity_band_start'].initial)
            form['quantity_band_end'].initial = normalize_fraction(form['quantity_band_end'].initial)
            form['weight_band_start'].initial = normalize_fraction(form['weight_band_start'].initial)
            form['weight_band_end'].initial = normalize_fraction(form['weight_band_end'].initial)
            form['pricing_native_amount'].initial = normalize_fraction(form['pricing_native_amount'].initial)

    @property
    def ipa_data_placeholder(self):
        if self.document_type == 'agreement':
            return "Please Select or Create an Into-Plane Agent"
        else:
            return "TBC / Confirmed on Order"

    def get_handler_qs(self):
        if self.document_type == 'agreement':
            return Organisation.objects.filter(
                Q(handler_details__airport__in=self.document.pricing_formulae.all().values('location')) |
                Q(handler_details__airport__in=self.document.pricing_manual.all().values('location'))
            ).distinct()
        else:
            return Organisation.objects.filter(
                handler_details__airport__in=self.document.pld_at_location.all().values('location'))

    def get_ipa_qs(self):
        if self.document_type == 'agreement':
            return Organisation.objects.filter(
                Q(ipa_locations__in=self.document.pricing_formulae.all().values('location')) |
                Q(ipa_locations__in=self.document.pricing_manual.all().values('location'))
            ).distinct()
        else:
            return Organisation.objects.filter(ipa_locations__in=self.document.pld_at_location.all().values('location'))

    def get_location_qs(self):
        if self.document_type == 'agreement':
            return Organisation.objects.filter(
                Q(airport_details__organisation__in=self.document.pricing_formulae.all().values('location')) |
                Q(airport_details__organisation__in=self.document.pricing_manual.all().values('location'))
            ).distinct()
        else:
            return Organisation.objects.filter(
                airport_details__organisation__in=self.document.pld_at_location.all().values('location'))

    def create_handler_field(self, form, form_number, value):
        '''
        Creates a new Specific Handler field
        '''
        handler_qs = self.get_handler_qs()

        form.fields[f'specific_handler-additional-{value}'] = \
            CustomModelChoiceField(required=False, queryset=handler_qs,
                                   widget=HandlerPickWidget(
                                       queryset=handler_qs,
                                       dependent_fields={
                                           f'new-fuel-fee-rate-{form_number}-location-additional-{value}': 'handler_details__airport'},
                                       context='formset', form_name=f'new-fuel-fee-rate-{form_number}'))

    def create_ipa_field(self, form, form_number, value):
        '''
        Creates a new IPA field, used because when called in a template, it registers itself in the redis cache, so even
        when we clone fields on the frontend, the dependent field functionality is still going to work
        '''
        ipa_qs = self.get_ipa_qs()

        form.fields[f'ipa-additional-{value}'] = \
            CustomModelChoiceField(required=False, queryset=ipa_qs,
                                   widget=IpaOrganisationPickCreateWidget(
                                       attrs={'data-placeholder': self.ipa_data_placeholder},
                                       queryset=ipa_qs, dependent_fields={
                                           f'new-fuel-fee-rate-{form_number}-location-additional-{value}': 'ipa_locations'},
                                       context='formset', form_name=f'new-fuel-fee-rate-{form_number}'))

    def add_fields(self, form, index):
        super(CombinedFuelFeeFormSet, self).add_fields(form, index)

        if self.context == 'Create' or self.context == 'Edit':
            location_qs = self.get_location_qs()
            ipa_qs = self.get_ipa_qs()
            handler_qs = self.get_handler_qs()

            # There might be a reason to give more rows than locations present
            if self.extra_location_fields:
                for form_number, rows in self.extra_location_fields.items():
                    rows = 4 if rows == 0 else rows
                    for value in range(int(rows)):
                        if index == form_number:
                            form.fields[f'location-additional-{value + 1}'] = \
                                forms.ModelChoiceField(queryset=location_qs, required=False,
                                                       widget=s2forms.Select2Widget(attrs={'class': 'form-control',
                                                                                           'data-placeholder': 'Select an Airport'}))

                            form.fields[
                                f'location-additional-{value + 1}'].label_from_instance = self.location_label_from_instance

                            form.fields[f'ipa-additional-{value + 1}'] = \
                                CustomModelChoiceField(required=False, queryset=ipa_qs,
                                                       widget=IpaOrganisationPickCreateWidget(
                                                           attrs={'data-placeholder': self.ipa_data_placeholder},
                                                           queryset=ipa_qs, dependent_fields={
                                                               f'new-fuel-fee-rate-{form_number}-location-additional-{value + 1}': 'ipa_locations'},
                                                           context='formset',
                                                           form_name=f'new-fuel-fee-rate-{form_number}'))

                            form.fields[f'pricing_native_unit-additional-{value + 1}'] = \
                                forms.ModelChoiceField(queryset=PricingUnit.objects.all(), required=False,
                                                       widget=FuelFeeUomPickWidget(attrs={'class': 'form-control',
                                                                                          'data-placeholder': 'Select Native Pricing Unit'}))

                            form.fields[
                                f'pricing_native_unit-additional-{value + 1}'].label_from_instance = self.pricing_native_unit_label_from_instance

                            form.fields[f'pricing_native_amount-additional-{value + 1}'] = \
                                forms.DecimalField(required=False,
                                                   widget=widgets.NumberInput(attrs={
                                                       'step': 0.000001,
                                                       'class': 'form-control auto-round-to-step'}))

                            form.fields[f'specific_handler-additional-{value + 1}'] = \
                                forms.ModelChoiceField(required=False, queryset=handler_qs,
                                                       widget=HandlerPickWidget(
                                                           queryset=handler_qs,
                                                           dependent_fields={
                                                               f'new-fuel-fee-rate-{form_number}-location-additional-{value + 1}': 'handler_details__airport'},
                                                           context='formset',
                                                           form_name=f'new-fuel-fee-rate-{form_number}'))

                            form.fields[f'specific_handler_is_excluded-additional-{value + 1}'] = \
                                forms.BooleanField(
                                    required=False,
                                    widget=widgets.CheckboxInput(attrs={
                                        'class': 'd-block form-field-w-100',
                                        'data-toggle': 'toggle',
                                        'data-on': 'Yes',
                                        'data-off': 'No',
                                        'data-onstyle': 'primary',
                                        'data-offstyle': 'primary',
                                    })
                                )

                            form.fields[f'specific_apron-additional-{value + 1}'] = \
                                forms.ModelChoiceField(required=False, queryset=ApronType.objects.all(),
                                                       widget=ApronTypePickWidget(
                                                           context='formset',
                                                           form_name=f'new-fuel-fee-rate-{form_number}'))

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'quantity_band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': 'form-control'}))

                        form.fields[f'quantity_band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': 'form-control'}))

                        form.fields[f'weight_band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': 'form-control'}))

                        form.fields[f'weight_band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': 'form-control'}))

                        if self.context == 'Supersede':
                            related_entries = SupplierFuelFeeRate.objects.filter(
                                supplier_fuel_fee_id=form['supplier_fuel_fee'].initial) \
                                                  .order_by('quantity_band_start', 'weight_band_start')[1:]

                            if value < related_entries.count():
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                       widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                                         'disabled': 'disabled'}))
                            else:
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                       widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                                         'disabled': 'disabled'}))

                        form.fields[f'band_pricing_native_amount-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                               widget=widgets.NumberInput(
                                                   attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step'}))

        elif self.related_entries:
            related_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee_id=form['supplier_fuel_fee'].initial) \
                                  .order_by('quantity_band_start', 'weight_band_start')[1:]
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'quantity_band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.quantity_band_start),
                                       widget=widgets.NumberInput(attrs={'step': 1,
                                                                         'class': 'form-control auto-round-to-step'}))

                form.fields[f'quantity_band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.quantity_band_end),
                                       widget=widgets.NumberInput(attrs={'step': 1,
                                                                         'class': 'form-control auto-round-to-step'}))

                form.fields[f'weight_band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.weight_band_start),
                                       widget=widgets.NumberInput(attrs={'step': 1,
                                                                         'class': 'form-control auto-round-to-step'}))

                form.fields[f'weight_band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.weight_band_end),
                                       widget=widgets.NumberInput(attrs={'step': 1,
                                                                         'class': 'form-control auto-round-to-step'}))

                if self.context == 'Supersede':
                    form.fields[f'pricing_native_amount_old-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(entry.pricing_native_amount),
                                           widget=widgets.NumberInput(
                                               attrs={'step': 0.0001, 'class': 'form-control', 'disabled': 'disabled'}))

                form.fields[f'band_pricing_native_amount-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(
                        entry.pricing_native_amount) if self.context != 'Supersede' else '',
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': 'form-control auto-round-to-step'}))

        # ADD/POPULATE VALIDITY PERIOD FIELDS
        additional_row_count = 0
        validity_period_row_fields = {
            'valid_from_dow': 'col-md-3 mb-3',
            'valid_to_dow': 'col-md-3 mb-3',
            'valid_from_time': 'col-md-2 mb-3',
            'valid_to_time': 'col-md-2 mb-3',
            'valid_all_day': 'col-md-1 mb-3'
        }

        # Get additional field count on POST
        if self.extra_period_fields:
            additional_row_count = self.extra_period_fields[index]

        # Prepare and populate additional period rows
        for value in range(0, int(additional_row_count)):
            for field_name, wrapper_classes in validity_period_row_fields.items():
                form.fields[f'{field_name}-additional-{value + 1}'] = deepcopy(form.fields[field_name])
                form.fields[
                    f'{field_name}-additional-{value + 1}'].group = f'additional-period-row-{value + 1}'
                form.fields[f'{field_name}-additional-{value + 1}'].wrapper_classes = wrapper_classes

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.airport_details.fullname}'

    @staticmethod
    def pricing_native_unit_label_from_instance(obj):
        return f'{obj.description}'

    def clean(self):
        for form_number, form in enumerate(self.forms):
            cleaned_data_copy = form.cleaned_data.copy()

            if form.cleaned_data.get('delivery_method') is None:
                form.errors.pop('delivery_method', None)

            if form.cleaned_data.get('specific_fuel') is None:
                form.errors.pop('specific_fuel', None)

            if form.cleaned_data.get('pricing_native_amount') is None and form.cleaned_data.get(
                'band_pricing_native_amount') is not None:
                for error in list(form.errors):
                    if 'pricing_native_amount' in error:
                        del form._errors['pricing_native_amount']

            if form.has_changed():
                if not form.cleaned_data.get('applies_to_private') and not form.cleaned_data.get(
                    'applies_to_commercial'):
                    form.add_error('applies_to_private', 'One of the checkboxes needs to be checked')
                    form.add_error('applies_to_commercial', '')

                if self.document_type == 'agreement':
                    if self.document.end_date and form.cleaned_data.get('valid_from_date') is not None \
                        and form.cleaned_data.get('valid_from_date') > self.document.end_date.date():
                        form.add_error('valid_from_date',
                                       f'The valid from date cannot be later than the end date of'
                                       f' the agreement ({self.document.end_date.strftime("%Y-%m-%d")})')

            if form.cleaned_data.get('DELETE'):
                for error in list(form.errors):
                    del form._errors[error]

                continue

            instances_of_band_1 = 0
            instances_of_band_2 = 0

            has_band_pricing = False
            for field, value in form.cleaned_data.items():
                if 'quantity_band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_1 += 1
                if 'weight_band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_2 += 1

            if has_band_pricing:
                # Earlier validation fail makes the quantity_band_uom value in cleaned_data None
                if not form.errors.get('quantity_band_uom'):
                    if form.cleaned_data.get('quantity_band_uom') is None and instances_of_band_1 != 0:
                        form.add_error('quantity_band_uom', 'Please Specify a Quantity Band')

                if form.cleaned_data.get('weight_band') is None and instances_of_band_2 != 0:
                    form.add_error('band_2_type', 'Please Specify a Weight Band')

                if form.cleaned_data.get('quantity_band_uom') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'quantity_band', 'integer')

                if form.cleaned_data.get('weight_band') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'weight_band', 'integer')

                for field, value in form.cleaned_data.items():
                    if self.context == 'Supersede':
                        if 'band_pricing_native_amount-additional' in field and value is None:
                            form.add_error(field, '')
                    else:
                        if 'band_pricing' in field and value is None:
                            form.add_error(field, '')

            # Because we are iterating over many fields, store if IPA required for each row to prevent repeated queries
            locations_ipa_required = {}

            for field, value in cleaned_data_copy.items():
                if self.document_type == 'agreement':
                    ipa_required = True
                else:
                    try:
                        ipa_required = True
                        row = re.findall("\d+", field)[0]
                        row_location = form.cleaned_data.get(f'location-additional-{row}')

                        # We can only know if IPA is required if row location is actually known,
                        # otherwise assume that it is always needed.
                        if row_location:
                            if row_location.pk in locations_ipa_required:
                                ipa_required = locations_ipa_required[row_location.pk]
                            else:
                                pricing_pks = row_location.fuel_pricing_market_plds_at_location\
                                    .filter(pld=self.document).values_list('fuel_pricing_market__pk', flat=True)

                                ipa_required = not FuelPricingMarket.objects.filter(
                                    Q(pk__in=pricing_pks) & Q(deleted_at__isnull=True)
                                    & Q(price_active=True) & Q(ipa__isnull=True)
                                ).exists()
                                locations_ipa_required[row_location.pk] = ipa_required
                    except IndexError:
                        continue

                if 'location-additional' in field and value is not None:
                    row = re.findall("\d+", field)[0]
                    # We only know if IPA is required if location is known, assume it's required otherwise
                    # if ipa_required:
                    if ipa_required and form.cleaned_data.get(
                        f'ipa-additional-{row}') is None and f'ipa-additional-{row}' not in form.errors:
                        form.add_error(f'ipa-additional-{row}', 'Please Select or Create an IPA')

                    if form.cleaned_data.get(
                        f'pricing_native_unit-additional-{row}') is None and f'pricing_native_unit-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_unit-additional-{row}', 'Please Select a Pricing Unit')
                    if form.cleaned_data.get(
                        f'pricing_native_amount-additional-{row}') is None and not has_band_pricing and f'pricing_native_amount-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_amount-additional-{row}', '')

                elif 'ipa-additional' in field and value is not None:
                    row = re.findall("\d+", field)[0]
                    if form.cleaned_data.get(
                        f'location-additional-{row}') is None and f'location-additional-{row}' not in form.errors:
                        form.add_error(f'location-additional-{row}', 'Please Select a Location')
                    if form.cleaned_data.get(
                        f'pricing_native_unit-additional-{row}') is None and f'pricing_native_unit-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_unit-additional-{row}', 'Please Select a Pricing Unit')
                    if form.cleaned_data.get(
                        f'pricing_native_amount-additional-{row}') is None and not has_band_pricing and f'pricing_native_amount-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_amount-additional-{row}', '')

                elif 'pricing_native_unit-additional' in field and value is not None:
                    row = re.findall("\d+", field)[0]
                    if form.cleaned_data.get(
                        f'location-additional-{row}') is None and f'location-additional-{row}' not in form.errors:
                        form.add_error(f'location-additional-{row}', 'Please Select a Location')
                    if ipa_required and form.cleaned_data.get(
                        f'ipa-additional-{row}') is None and f'ipa-additional-{row}' not in form.errors:
                        form.add_error(f'ipa-additional-{row}', 'Please Select or Create an IPA')
                    if form.cleaned_data.get(
                        f'pricing_native_amount-additional-{row}') is None and not has_band_pricing and f'pricing_native_amount-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_amount-additional-{row}', '')

                elif 'pricing_native_amount-additional' in field and value is not None and not has_band_pricing:
                    row = re.findall("\d+", field)[0]
                    if form.cleaned_data.get(
                        f'location-additional-{row}') is None and f'location-additional-{row}' not in form.errors:
                        form.add_error(f'location-additional-{row}', 'Please Select a Location')
                    if ipa_required and form.cleaned_data.get(
                        f'ipa-additional-{row}') is None and f'ipa-additional-{row}' not in form.errors:
                        form.add_error(f'ipa-additional-{row}', 'Please Select or Create an IPA')
                    if form.cleaned_data.get(
                        f'pricing_native_unit-additional-{row}') is None and f'pricing_native_unit-additional-{row}' not in form.errors:
                        form.add_error(f'pricing_native_unit-additional-{row}', 'Please Select a Pricing Unit')

        self.validate_unique()


CombinedFuelFeeRateFormset = modelformset_factory(SupplierFuelFeeRate,
                                                  can_delete=True,
                                                  extra=0,
                                                  form=CombinedFuelFeeForm,
                                                  formset=CombinedFuelFeeFormSet
                                                  )

NewCombinedFuelFeeRateFormset = modelformset_factory(SupplierFuelFeeRate,
                                                     extra=10,
                                                     can_delete=True,
                                                     form=CombinedFuelFeeForm,
                                                     formset=CombinedFuelFeeFormSet
                                                     )
