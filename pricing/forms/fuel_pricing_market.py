from datetime import timedelta

from django import forms
from django.db import transaction
from django.forms import BaseModelFormSet, modelformset_factory, widgets
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django_select2 import forms as s2forms

from core.form_widgets import HookupMethodPickWidget
from core.models import FuelType, GeographichFlightType, HookupMethod, UnitOfMeasurement
from organisation.form_widgets import AirportPickWidget, OrganisationPickWidget, OrganisationWithTypePickWidget
from organisation.models.organisation import Organisation
from pricing.fields import InclusiveTaxesFormField
from pricing.form_widgets import ApronTypePickWidget, ClientPickWidget, FuelQuantityPricingUnitPickWidget, \
    HandlerPickWidget, IpaOrganisationPickCreateWidget
from pricing.models import FuelPricingMarket, FuelPricingMarketPld, FuelPricingMarketPldDocument, \
    FuelPricingMarketPldLocation, TaxCategory
from pricing.utils.tax import validate_band_rows
from pricing.utils.fuel_pricing_market import normalize_fraction


# Used for creating a new PLD or editing the current one's name
class FuelPricingMarketPldForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # I believe this shouldn't be modified, as it is used for pricing entries
        # Instead, a new PLD should be created
        if self.instance.pk is not None:
            self.fields['supplier'].disabled = True

    class Meta:
        model = FuelPricingMarketPld
        fields = ['supplier', 'pld_name', 'priority']

        widgets = {
            'supplier': OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
            'pld_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'priority': s2forms.Select2Widget(attrs={
                'class': 'form-control',
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        pld_name = self.cleaned_data['pld_name']
        supplier = self.cleaned_data['supplier']
        pld_pk = getattr(self.instance, 'pk', None)

        if FuelPricingMarketPld.objects.filter(pld_name=pld_name, supplier=supplier).exclude(pk=pld_pk).exists() and self.instance.id is None:
            self.add_error('pld_name', f'Document with this name already exists in the database.')

        return cleaned_data

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def save(self, commit=True):
        document = super().save(commit=False)
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    is_new_pld = self.instance.pk is None
                    document.updated_by = self.request.user.person
                    document.save()
                    if is_new_pld:
                        self.request.session[f'pld-{document.id}'] = 'new'

        return document


# Used to attach new document to the PLD
class PLDDocumentsForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        self.pld_document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = FuelPricingMarketPldDocument
        fields = ['name', 'description', 'file', ]
        widgets = {
            "name": widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            "description": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),

            "file": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
        }

    def save(self, commit=True):
        document = super().save(commit=False)
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    document.pld = self.pld_document
                    document.save()

        return document


# Used for superseding existing fuel pricing and creating/editing
class FuelPricingMarketFuelPricingForm(forms.ModelForm):
    inclusive_taxes = InclusiveTaxesFormField()
    cascade_to_fees = forms.BooleanField(label='Cascade to Fees?',
                                         required=False,
                                         widget=forms.CheckboxInput(attrs={
                                             'class': 'form-check-input d-block mt-2',
                                         })
                                         )

    pricing_native_amount_old = forms.DecimalField(required=False,
        widget = widgets.NumberInput(attrs={
            'class': 'form-control set-width',
            'disabled': 'disabled'
        })
    )

    location = FuelPricingMarketPldLocation.location.field.formfield(
        widget=AirportPickWidget(
            attrs={'class': 'form-control',
                   'data-placeholder': 'Select Location'}),
    )

    band_pricing_native_amount = forms.DecimalField(required=False,
                                    widget=widgets.NumberInput(attrs={'step': 0.000001,
                                                                      'class': 'form-control auto-round-to-step'}))

    specific_hookup_method = forms.ModelChoiceField(
        empty_label='All',
        label='Hookup Method',
        queryset=HookupMethod.objects.all(),
        widget=HookupMethodPickWidget(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        self.pld_instance = kwargs.pop('pld_instance', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        self.fields['supplier_pld_location'].required = False
        self.fields['ipa'].required = False
        self.fields['ipa'].empty_label = 'TBC / Confirmed on Order'

        self.fields['inclusive_taxes'].choices = [('A', 'All Applicable Taxes')] + list(
            TaxCategory.objects.order_by('name').values_list('pk', 'name'))

        if self.context == 'Supersede':
            self.fields['supplier_pld_location'].label_from_instance = self.location_label_from_instance
            self.fields['supplier_pld_location'].disabled = True
            self.fields['supplier_pld_location'].queryset = \
                FuelPricingMarketPldLocation.objects.filter(id = self.instance.supplier_pld_location_id)
            self.fields['location'].required = False

            if self.instance.pk:
                self.fields['inclusive_taxes'].initial, self.fields['cascade_to_fees'].initial = \
                    self.instance.inclusive_taxes

            self.fields['ipa'].disabled = True
            self.fields['ipa'].queryset = Organisation.objects.filter(
                pk=getattr(self.instance.ipa, 'pk', None))
            self.fields['ipa'].help_text = self.instance.ipa.details.registered_name \
                if self.instance.ipa else 'TBC / Confirmed on Order'
            self.fields['ipa'].label_from_instance = self.ipa_label_from_instance

        elif self.context == 'Edit':
            self.fields['location'].initial = self.entry.supplier_pld_location.location
            self.fields['location'].disabled = True

            ipas_qs = self.fields['ipa'].queryset
            pricing_location = self.instance.supplier_pld_location.location

            self.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                attrs={"data-placeholder": 'TBC / Confirmed on Order'},
                queryset=ipas_qs.filter(ipa_locations=pricing_location),
                # dependent_fields={'location': 'ipa_locations_here'},
                airport_location=pricing_location)


        if self.instance.band_start is not None:
            self.fields['band_pricing_native_amount'].initial = normalize_fraction(self.instance.pricing_native_amount)

        self.fields['fuel'].queryset = FuelType.objects.with_custom_ordering()

        self.fields['ipa'].error_messages['invalid_choice'] = "This Organisation already exists and can't be selected."

        self.fields['destination_type'].queryset = GeographichFlightType.objects.filter(code__in = ['ALL', 'INT', 'DOM'])

        self.fields['pricing_native_unit'].label_from_instance = self.pricing_native_unit_label_from_instance
        self.fields['pricing_converted_unit'].label_from_instance = self.pricing_native_unit_label_from_instance

        self.fields['band_uom'].queryset = UnitOfMeasurement.objects.fluid_with_custom_ordering()
        self.fields['band_uom'].label_from_instance = self.band_unit_label_from_instance

    @staticmethod
    def ipa_label_from_instance(obj):
        return f'{obj.details.registered_name}'

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.location.airport_details.icao_iata}'

    @staticmethod
    def pricing_native_unit_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def band_unit_label_from_instance(obj):
        return f'{obj.description_plural}'

    class Meta:
        model = FuelPricingMarket
        fields = ['location', 'ipa', 'delivery_methods', 'fuel', 'pricing_native_unit',
                  'pricing_native_amount', 'supplier_exchange_rate', 'pricing_converted_unit',
                  'pricing_converted_amount', 'flight_type', 'destination_type', 'band_uom', 'band_start', 'band_end',
                  'band_pricing_native_amount', 'valid_from_date', 'valid_to_date', 'comments',
                  'pricing_native_amount_old', 'supplier_pld_location', 'applies_to_private', 'applies_to_commercial',
                  'is_pap', 'inclusive_taxes', 'cascade_to_fees', 'client', 'specific_handler', 'specific_apron',
                  'specific_hookup_method']

        widgets = {
            'supplier_pld_location': widgets.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select Location'
            }),
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'is_pap': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'ipa': widgets.Select(attrs={
                'class': 'form-control form-field-w-100',
                'placeholder': 'Select an Into-Plane Agent'
            }),
            'delivery_methods': s2forms.Select2MultipleWidget(attrs={
                'class': 'form-control',
                "data-placeholder": "Applies to All Methods",
            }),
            'fuel': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Fuel Type'
            }),
            'pricing_native_unit': FuelQuantityPricingUnitPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Native Pricing Unit',
            }),
            'pricing_native_amount': widgets.NumberInput(attrs={
                'class': 'form-control set-width auto-round-to-step',
                'placeholder': ' '
            }),
            'supplier_exchange_rate': widgets.NumberInput(attrs={
                'class': 'form-control auto-round-to-step'
            }),
            'pricing_converted_unit': FuelQuantityPricingUnitPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Supplier Converted Pricing Unit',
            }),
            'pricing_converted_amount': widgets.NumberInput(attrs={
                'class': 'form-control'
        }),
            'flight_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Type'
            }),
            'destination_type': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Applicable Flight Destination',
            }),
            'client': ClientPickWidget(attrs={
                'class': 'form-control',
            }),
            'specific_handler': HandlerPickWidget(attrs={
                'class': 'form-control',
            }),
            'specific_apron': ApronTypePickWidget(attrs={
                'class': 'form-control',
            }),
            'band_uom': s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Fluid Band Type'
            }),
            'band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
            }),
            'band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1
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
            'comments': widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
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


class BaseFuelPricingFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('pld_instance', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        self.related_entries = kwargs.pop('related_entries', None)
        self.dates_entered = kwargs.pop('dates_entered', None)
        self.importer_updates = kwargs.pop('importer_updates', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Supersede':
            locations = self.document.pld_at_location.all()
            self.queryset = FuelPricingMarket.objects.filter(price_active = True, parent_entry = None,
                                                             supplier_pld_location__in = locations)

            if self.importer_updates:
                self.management_form.fields['require_change_in_fees'] = forms.BooleanField(
                    initial=self.importer_updates['changes_to_fees'], widget=forms.HiddenInput())
                self.management_form.fields['require_change_in_taxes'] = forms.BooleanField(
                    initial=self.importer_updates['changes_to_taxes'], widget=forms.HiddenInput())
            else:
                self.management_form.fields['require_change_in_fees'] = forms.BooleanField(
                    initial=False, widget=forms.HiddenInput())
                self.management_form.fields['require_change_in_taxes'] = forms.BooleanField(
                    initial=False, widget=forms.HiddenInput())

            for form in self.forms:
                form['pricing_native_amount_old'].initial = normalize_fraction(form['pricing_native_amount'].initial)
                form['pricing_native_amount'].initial = ''
                form['valid_from_date'].initial = form['valid_to_date'].initial + timedelta(days=1)
                form['valid_to_date'].initial = ""

                form['band_start'].initial = normalize_fraction(form['band_start'].initial)
                form['band_end'].initial = normalize_fraction(form['band_end'].initial)

                parent_pk = str(form.fields['id'].initial)

                # If overriding data from CSV importer present, use it to prepopulate fields
                if self.importer_updates is not None:
                    if parent_pk in self.importer_updates:
                        new_data = self.importer_updates[parent_pk]
                        form['pricing_native_amount'].initial = new_data['new_pricing_native_amount']
                        form['valid_from_date'].initial = new_data['new_valid_from']
                        form['valid_to_date'].initial = new_data['new_valid_to']
                    else:
                        # Pricing that was not in the imported CSV should not be superseded, so we mark it as deleted
                        form["DELETE"].initial = True

        elif self.context == 'Edit':
            self.queryset = FuelPricingMarket.objects.filter(id = self.entry.pk, price_active = True)

            for form in self.forms:
                form['pricing_native_amount'].initial = normalize_fraction(form['pricing_native_amount'].initial)
                form['band_start'].initial = normalize_fraction(form['band_start'].initial)
                form['band_end'].initial = normalize_fraction(form['band_end'].initial)
                form['inclusive_taxes'].initial, form['cascade_to_fees'].initial = self.entry.inclusive_taxes

        # On creation
        else:
            self.queryset = FuelPricingMarket.objects.none()

            for value, form in enumerate(self.forms):
                form.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                    attrs={"data-placeholder": 'TBC / Confirmed on Order'},
                    dependent_fields={f'new-pricing-{value}-location': 'ipa_locations'},
                    context='formset', form_name=f'new-pricing-{value}')

        # Register dependent fields
        prefix = 'existing-pricing' if self.context == 'Supersede' else 'new-pricing'
        field_name = 'supplier_pld_location' if self.context == 'Supersede' else 'location'
        model_field = 'handler_details__airport__fuel_pricing_market_plds_at_location' if self.context == 'Supersede' else 'handler_details__airport'

        for value, form in enumerate(self.forms):
            form.fields['specific_handler'].widget = HandlerPickWidget(
                queryset=Organisation.objects.handling_agent(),
                dependent_fields={
                    f'{prefix}-{value}-{field_name}': f'{model_field}'},
                attrs={'class': 'form-control'}
            )

        if len(self.forms) > 0:
            self.forms[0].empty_permitted = False


    def add_fields(self, form, index):
        super(BaseFuelPricingFormSet, self).add_fields(form, index)
        related_entries = FuelPricingMarket.objects.filter(parent_entry = form['id'].initial, price_active = True)\
                                                   .order_by('band_start')

        if self.context == 'Supersede':
            classes = 'form-control band-width'
        else:
            classes = 'form-control'

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'band_start-additional-{form_number}-{value+1}'] = \
                                    forms.IntegerField(required=False,
                                    widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        form.fields[f'band_end-additional-{form_number}-{value+1}'] = \
                                    forms.IntegerField(required=False,
                                    widget=widgets.NumberInput(attrs={'class': f'{classes}'}))

                        if self.context == 'Supersede':
                            if value < related_entries.count():
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value+1}'] = \
                                        forms.DecimalField(required=False,
                                        widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                          'disabled': 'disabled'}))
                            else:
                                form.fields[f'pricing_native_amount_old-additional-{form_number}-{value+1}'] = \
                                        forms.DecimalField(required=False,
                                        widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                        'disabled': 'disabled'}))

                        form.fields[f'band_pricing_native_amount-additional-{form_number}-{value+1}'] = \
                                    forms.DecimalField(required=True,
                                    widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                      'class': 'form-control auto-round-to-step'}))

        elif self.related_entries or self.context == 'Supersede':
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'band_start-additional-{form_number}-{value+1}'] = \
                            forms.IntegerField(required=False, initial=normalize_fraction(entry.band_start),
                            widget=widgets.NumberInput(attrs={'step': 1, 'class': f'{classes} auto-round-to-step'}))

                form.fields[f'band_end-additional-{form_number}-{value+1}'] = \
                            forms.IntegerField(required=False, initial=normalize_fraction(entry.band_end),
                            widget=widgets.NumberInput(attrs={'step': 1, 'class': f'{classes} auto-round-to-step'}))

                if self.context == 'Supersede':

                    form.fields[f'pricing_native_amount_old-additional-{form_number}-{value+1}'] = \
                            forms.DecimalField(required=False, initial=normalize_fraction(entry.pricing_native_amount),
                            widget=widgets.NumberInput(attrs={'step': 0.000001, 'class': 'form-control', 'disabled': 'disabled'}))

                # Use initial price for the band from CSV Importer if available
                initial_price = self.importer_updates[str(entry.pk)].get('new_pricing_native_amount', None) \
                    if self.importer_updates is not None and str(entry.pk) in self.importer_updates else ''

                form.fields[f'band_pricing_native_amount-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(entry.pricing_native_amount)
                    if self.context != 'Supersede' else initial_price, widget=widgets.NumberInput(attrs={
                        'step': 0.000001, 'class': 'form-control auto-round-to-step'}))

    def clean(self):
        for form_number, form in enumerate(self.forms):

            # 'All' here is an empty label only, so we need to remove error (there are alternative solutions, this one
            # is the most painless)
            if form.cleaned_data.get('specific_hookup_method') is None:
                form.errors.pop('specific_hookup_method', None)

            if self.context == 'Create' and form.cleaned_data.get('location'):
                pld_location = FuelPricingMarketPldLocation.objects.filter(location = form.cleaned_data.get('location'),
                                                                       pld__supplier = self.document.supplier,
                                                                       pld__is_current = True)
                if pld_location.exists() and pld_location[0].pld_id != self.document.id:
                    raise forms.ValidationError(f'Supplier "{self.document.supplier.details.registered_name}" with pricing at\
                                                 {pld_location[0].location.airport_details.icao_iata} already exists!')

            if not form.cleaned_data.get('DELETED'):
                if form.cleaned_data.get('pricing_native_amount') is None and form.cleaned_data.get('band_pricing_native_amount') is not None:
                    del form._errors['pricing_native_amount']

                elif form.cleaned_data.get('pricing_native_amount') is None and \
                     form.cleaned_data.get('band_pricing_native_amount') is None and \
                     form.cleaned_data.get('band_uom') is not None:

                        form.add_error('band_pricing_native_amount', 'This field is required')
                        del form._errors['pricing_native_amount']

            if self.dates_entered:
                for error in list(form.errors):
                    if 'valid_to_date' in error or 'valid_from_date' in error:
                        del form.errors[error]

            if form.has_changed():
                if not form.cleaned_data.get('applies_to_private') and not form.cleaned_data.get('applies_to_commercial'):
                    form.add_error('applies_to_private', 'One of the checkboxes needs to be checked')
                    form.add_error('applies_to_commercial', '')

            instances_of_band_1 = 0
            has_band_pricing = False
            for field, value in form.cleaned_data.items():
                if 'band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_1 += 1

            cleaned_data_copy = form.cleaned_data.copy()

            if has_band_pricing:
                if form.cleaned_data.get('band_uom') is None and instances_of_band_1 != 0:
                    form.add_error('band_uom', 'This field is required when band pricing or multiple band rows are present')

                if form.cleaned_data.get('band_uom') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band', 'integer')

                for field, value in cleaned_data_copy.items():
                    if self.context == 'Supersede':
                        if 'band_pricing_native_amount-additional' in field and value is None:
                            form.add_error(field, '')
                    else:
                        if 'band_pricing' in field and value is None:
                            form.add_error(field, '')


            if form.cleaned_data.get('DELETE'):
                for error in list(form.errors):
                    del form.errors[error]

        self.validate_unique()

FuelPricingMarketPricingFormset = modelformset_factory(FuelPricingMarket,
            can_delete=True,
            extra=0,
            form=FuelPricingMarketFuelPricingForm,
            formset=BaseFuelPricingFormSet
            )

NewFuelPricingMarketPricingFormset = modelformset_factory(FuelPricingMarket,
            extra=50,
            can_delete=True,
            form=FuelPricingMarketFuelPricingForm,
            formset=BaseFuelPricingFormSet
            )

# Used on Fuel Pricing Supersede to set dates for all rows
# Used on Fuel Fee Supersede to set valid from dates for all rows
class PricingDatesSupersedeForm(forms.Form):

    apply_to_all = forms.BooleanField(widget = widgets.CheckboxInput(attrs={
                'class': 'header-date-open'
    }), required=False)

    valid_from = forms.DateField(widget = widgets.DateInput(attrs={
                'class': 'form-control date-input header-date-input',
                'type': 'text',
                'placeholder': 'Valid From'
            }), required=False)

    valid_to = forms.DateField(widget = widgets.DateInput(attrs={
                'class': 'form-control date-input header-date-input',
                'type': 'text',
                'placeholder': 'Valid To'}), required=False)

    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', None)
        super().__init__(*args, **kwargs)

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
        if self.context == 'fuel-pricing':
            if cleaned_data.get('apply_to_all') and not cleaned_data.get('valid_from') and not cleaned_data.get('valid_to'):
                self.add_error('valid_from', 'This field is required.')
                self.add_error('valid_to', 'This field is required.')
        else:
            if cleaned_data.get('apply_to_all') and not cleaned_data.get('valid_from'):
                self.add_error('valid_to', 'This field is required')
        return cleaned_data


class FuelPricingMarketPldBillableOrganisationsForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].disabled = True

        # For some reason, the formset includes a blank form at the end with a new instance, despite extra=0
        if self.instance.pk:
            self.fields['billable_organisation'].widget.attrs['data-placeholder'] \
                = f'Supplier ({self.instance.pld.supplier.details.registered_and_trading_name})'

    class Meta:
        model = FuelPricingMarketPldLocation
        fields = ['id', 'location', 'billable_organisation']

        widgets = {
            'id': forms.HiddenInput(),
            'location': AirportPickWidget(attrs={
                'class': 'form-control',
            }),
            'billable_organisation': OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
        }


class BaseFuelPricingMarketPldBillableOrganisationsFormset(BaseModelFormSet):
    pass


FuelPricingMarketPldBillableOrganisationsFormset = modelformset_factory(
    FuelPricingMarketPldLocation,
    extra=0,
    form=FuelPricingMarketPldBillableOrganisationsForm,
    formset=BaseFuelPricingMarketPldBillableOrganisationsFormset,
)
