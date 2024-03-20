from django import forms
from django.db.models import Q
from django.forms import BaseModelFormSet, modelformset_factory, widgets
from django_select2 import forms as s2forms

from core.models import FuelType, GeographichFlightType, HookupMethod, UnitOfMeasurement
from core.form_widgets import HookupMethodPickWidget
from organisation.form_widgets import AirportPickWidget, OrganisationPickWidget
from organisation.models.organisation import Organisation
from pricing.fields import InclusiveTaxesFormField
from pricing.form_widgets import ApronTypePickWidget, ClientPickWidget, FuelIndexPickWidget, FuelIndexDetailsPickWidget, \
    FuelQuantityPricingUnitPickWidget, HandlerPickWidget, IpaOrganisationPickCreateWidget
from pricing.models import FuelAgreement, FuelAgreementPricingFormula, FuelAgreementPricingManual, FuelIndex,\
    TaxCategory
from pricing.utils import pricing_check_overlap
from pricing.utils.fuel_pricing_market import normalize_fraction
from pricing.utils.tax import validate_band_rows


###################
# FORMULA PRICING
###################

class FuelAgreementPricingFormulaPricingForm(forms.ModelForm):
    inclusive_taxes = InclusiveTaxesFormField()
    cascade_to_fees = forms.BooleanField(label='Cascade to Fees?',
                                         required=False,
                                         widget=forms.CheckboxInput(attrs={
                                             'class': 'form-check-input d-block mt-2',
                                         })
                                         )

    differential_value_old = forms.DecimalField(required=False,
                                                widget=widgets.NumberInput(attrs={
                                                    'class': 'form-control',
                                                    'disabled': 'disabled'
                                                }))

    band_differential_value = forms.DecimalField(required=False,
                                                 widget=widgets.NumberInput(
                                                     attrs={'step': 0.000001,
                                                            'class': 'form-control auto-round-to-step',
                                                            'placeholder': 'Differential',
                                                            }))

    fuel_index = forms.ModelChoiceField(required=True,
                                        queryset=FuelIndex.objects.all(),
                                        widget=FuelIndexPickWidget(
                                            attrs={
                                                'class': 'form-control',
                                            }))

    specific_hookup_method = forms.ModelChoiceField(
        empty_label='All',
        label='Hookup Method',
        queryset=HookupMethod.objects.all(),
        widget=HookupMethodPickWidget(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        self.agreement = kwargs.pop('agreement', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        super().__init__(*args, **kwargs)

        self.fields['inclusive_taxes'].choices = [('A', 'All Applicable Taxes')] + list(
            TaxCategory.objects.order_by('name').values_list('pk', 'name'))

        self.fields['band_differential_value'].label = 'Differential Value'

        if self.context == 'Supersede':
            self.fields['location'].widget = widgets.Select(attrs={
                'class': 'form-control form-field-w-100',
            })
            self.fields['location'].queryset = Organisation.objects.filter(
                pk=self.instance.location.pk)
            self.fields['location'].label_from_instance = self.location_label_from_instance
            self.fields['location'].disabled = True
            self.fields['inclusive_taxes'].initial, self.fields['cascade_to_fees'].initial = \
                self.instance.inclusive_taxes

            self.fields['ipa'].disabled = True
            self.fields['ipa'].queryset = Organisation.objects.filter(
                pk=getattr(self.instance.ipa, 'pk', None))
            self.fields['ipa'].help_text = self.instance.ipa.details.registered_name \
                if self.instance.ipa else 'TBC / Confirmed on Order'
            self.fields['ipa'].label_from_instance = self.ipa_label_from_instance

        elif self.context == 'Edit':
            self.fields['location'].initial = self.entry.location
            self.fields['location'].disabled = True

            ipas_qs = self.fields['ipa'].queryset
            pricing_location = self.entry.location

            self.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                queryset=ipas_qs.filter(ipa_locations=pricing_location),
                # dependent_fields={'location': 'ipa_locations_here'},
                airport_location=pricing_location, attrs={
                    'class': 'form-control',
                    'data-placeholder': 'Select an Into-Plane Agent'
                })

        if self.instance.band_start is not None:
            self.fields['band_differential_value'].initial = normalize_fraction(self.instance.differential_value)

        self.fields['fuel'].queryset = FuelType.objects.with_custom_ordering()

        self.fields['ipa'].error_messages['invalid_choice'] = "This Organisation already exists but can't be selected."

        self.fields['destination_type'].queryset = GeographichFlightType.objects.filter(code__in=['ALL', 'INT', 'DOM'])

        self.fields['differential_pricing_unit'].label_from_instance = self.differential_unit_label_from_instance

        self.fields['band_uom'].queryset = UnitOfMeasurement.objects.fluid_with_custom_ordering()
        self.fields['band_uom'].label_from_instance = self.band_unit_label_from_instance

        self.fields['pricing_index'].label = 'Index Structure'

        if getattr(self.instance, 'pricing_index', None):
            self.fields['fuel_index'].initial = self.instance.pricing_index.fuel_index

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.airport_details.icao_iata}'

    @staticmethod
    def ipa_label_from_instance(obj):
        return f'{obj.details.registered_name}'

    @staticmethod
    def differential_unit_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def band_unit_label_from_instance(obj):
        return f'{obj.description_plural}'

    class Meta:
        model = FuelAgreementPricingFormula
        fields = ['location', 'ipa', 'delivery_methods', 'fuel', 'fuel_index', 'pricing_index',
                  'index_period_is_lagged', 'index_period_is_grace', 'differential_pricing_unit', 'differential_value',
                  'volume_conversion_method', 'volume_conversion_ratio_override', 'flight_type', 'destination_type',
                  'band_uom', 'band_start', 'band_end', 'band_differential_value', 'comment', 'differential_value_old',
                  'applies_to_private', 'applies_to_commercial', 'inclusive_taxes', 'cascade_to_fees', 'client',
                  'specific_handler', 'specific_apron', 'specific_hookup_method']

        widgets = {
            'location': AirportPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Location',
                'icao_iata_label': True,
            }),
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
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
            'pricing_index': FuelIndexDetailsPickWidget(attrs={
                'class': 'form-control',
            }),
            'index_period_is_lagged': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'index_period_is_grace': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'differential_pricing_unit': FuelQuantityPricingUnitPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Differential Pricing Unit',
            }),
            'differential_value': widgets.NumberInput(attrs={
                'class': 'form-control set-width auto-round-to-step',
                'placeholder': 'Differential',
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
                'data-placeholder': 'Select Fluid Band Type',
                'data-allow-clear': 'true',
        }),
            'band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1,
                'placeholder': 'Band Start',
            }),
            'band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1,
                'placeholder': 'Band End',
            }),
            'volume_conversion_ratio_override': widgets.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 99999999.9999,
            }),
            'comment': widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }

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


class BaseFuelAgreementPricingFormulaFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.agreement = kwargs.pop('agreement', None)
        self.old_agreement = kwargs.pop('old_agreement', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        self.related_entries = kwargs.pop('related_entries', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Supersede':
            self.queryset = FuelAgreementPricingFormula.objects.filter(
                parent_entry=None, agreement=self.old_agreement)

            for form in self.forms:
                form['differential_value_old'].initial = normalize_fraction(form["differential_value"].initial)
                form['differential_value'].initial = ''
                form.fields['applies_to_private'].widget.attrs['class'] = 'form-check-input'
                form.fields['applies_to_commercial'].widget.attrs['class'] = 'form-check-input'

                form['band_start'].initial = normalize_fraction(form['band_start'].initial)
                form['band_end'].initial = normalize_fraction(form['band_end'].initial)

        elif self.context == 'Edit':
            self.queryset = FuelAgreementPricingFormula.objects.filter(id=self.entry.pk)

            self.forms[0]['band_start'].initial = normalize_fraction(self.forms[0]['band_start'].initial)
            self.forms[0]['band_end'].initial = normalize_fraction(self.forms[0]['band_end'].initial)

            for form in self.forms:
                form['differential_value'].initial = normalize_fraction(form['differential_value'].initial)

                form['inclusive_taxes'].initial, form['cascade_to_fees'].initial = self.entry.inclusive_taxes

        # On creation
        else:
            self.queryset = FuelAgreementPricingFormula.objects.none()

            for value, form in enumerate(self.forms):
                form.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                    dependent_fields={f'new-pricing-{value}-location': 'ipa_locations'},
                    context='formset', form_name=f'new-pricing-{value}', attrs={
                        'class': 'form-control',
                        'data-placeholder': 'Select an Into-Plane Agent'
                    })

        # Register dependent fields for fuel pricing index / index structure
        prefix = 'existing-formula-pricing' if self.context == 'Supersede' else 'new-pricing'

        for value, form in enumerate(self.forms):
            form.fields['pricing_index'].widget = FuelIndexDetailsPickWidget(
                dependent_fields={f'{prefix}-{value}-fuel_index': 'fuel_index'},
                attrs={
                    'class': 'form-control',
                }
            )

        # Register dependent fields
        prefix = 'existing-formula-pricing' if self.context == 'Supersede' else 'new-pricing'

        for value, form in enumerate(self.forms):
            form.fields['specific_handler'].widget = HandlerPickWidget(
                queryset=Organisation.objects.handling_agent(),
                dependent_fields={
                    f'{prefix}-{value}-location': 'handler_details__airport'},
                attrs={'class': 'form-control'}
            )

        if len(self.forms) > 0:
            self.forms[0].empty_permitted = False

    def add_fields(self, form, index):
        super(BaseFuelAgreementPricingFormulaFormSet, self).add_fields(form, index)
        related_entries = FuelAgreementPricingFormula.objects \
            .filter(parent_entry=form['id'].initial) \
            .order_by('band_start')

        if self.context == 'Supersede':
            classes = 'form-control band-width auto-round-to-step'
        else:
            classes = 'form-control'

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}',
                                                                                 'placeholder': 'Band Start'}))

                        form.fields[f'band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}',
                                                                                 'placeholder': 'Band End'}))

                        if self.context == 'Supersede':
                            if value < related_entries.count():
                                form.fields[f'differential_value_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                                       'disabled': 'disabled'}))
                            else:
                                form.fields[f'differential_value_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                                       'disabled': 'disabled'}))

                        form.fields[f'band_differential_value-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.000001, 'class': 'form-control auto-round-to-step',
                                                        'placeholder': 'Differential', }))

        elif self.related_entries or self.context == 'Supersede':
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.band_start),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step',
                                                                         'placeholder': 'Band Start'}))

                form.fields[f'band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.band_end),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step',
                                                                         'placeholder': 'Band End'}))

                if self.context == 'Supersede':
                    form.fields[f'differential_value_old-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(entry.differential_value),
                                         widget=widgets.NumberInput(
                                             attrs={'step': 0.000001, 'class': 'form-control', 'disabled': 'disabled'}))

                form.fields[f'band_differential_value-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(
                        entry.differential_value) if self.context != 'Supersede' else '',
                                     widget=widgets.NumberInput(attrs={'step': 0.000001,
                                                                       'class': 'form-control auto-round-to-step',
                                                                       'placeholder': 'Differential', }))



    def clean(self):
        # Get other supplier agreements to check for overlaps
        supplier_agreements = FuelAgreement.objects \
            .filter(Q(supplier=self.agreement.supplier) & ~Q(pk=self.agreement.pk)) \
            .prefetch_related('pricing_formulae', 'pricing_manual')

        for form_number, form in enumerate(self.forms):
            location = form.cleaned_data.get('location')

            if location:
                ipa = form.cleaned_data.get('ipa')
                overlap_msg = pricing_check_overlap(location, ipa, self.agreement, supplier_agreements)

                if overlap_msg:
                    form.add_error(None, forms.ValidationError(overlap_msg))

            # 'All' here is an empty label only, so we need to remove error (there are alternative solutions, this one
            # is the most painless)
            if form.cleaned_data.get('specific_hookup_method') is None:
                form.errors.pop('specific_hookup_method', None)

            if not form.cleaned_data.get('DELETED'):
                if form.cleaned_data.get('differential_value') is None and \
                    form.cleaned_data.get('band_differential_value') is not None:
                    del form._errors['differential_value']

                elif form.cleaned_data.get('differential_value') is None and \
                    form.cleaned_data.get('band_differential_value') is None and \
                    form.cleaned_data.get('band_uom') is not None:

                    form.add_error('band_differential_value', 'This field is required')
                    del form._errors['differential_value']

            if form.has_changed():
                if not form.cleaned_data.get('applies_to_private') and \
                    not form.cleaned_data.get('applies_to_commercial'):
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
                    form.add_error('band_uom',
                                   'This field is required when band pricing or multiple band rows are present')

                if form.cleaned_data.get('band_uom') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band', 'integer')

                for field, value in cleaned_data_copy.items():
                    if self.context == 'Supersede':
                        if 'band_differential_value-additional' in field and value is None:
                            form.add_error(field, '')
                    else:
                        if 'band_differential_value' in field and value is None:
                            form.add_error(field, '')

            if form.cleaned_data.get('DELETE'):
                for error in list(form.errors):
                    del form.errors[error]

        self.validate_unique()


FuelAgreementPricingFormulaFormset = modelformset_factory(FuelAgreementPricingFormula,
                                                          can_delete=True,
                                                          extra=0,
                                                          form=FuelAgreementPricingFormulaPricingForm,
                                                          formset=BaseFuelAgreementPricingFormulaFormSet
                                                          )

NewFuelAgreementPricingFormulaFormset = modelformset_factory(FuelAgreementPricingFormula,
                                                             extra=30,
                                                             can_delete=True,
                                                             form=FuelAgreementPricingFormulaPricingForm,
                                                             formset=BaseFuelAgreementPricingFormulaFormSet
                                                             )



###################
# DISCOUNT PRICING
###################

class FuelAgreementPricingDiscountPricingForm(forms.ModelForm):
    inclusive_taxes = InclusiveTaxesFormField()
    cascade_to_fees = forms.BooleanField(label='Cascade to Fees?',
                                         required=False,
                                         widget=forms.CheckboxInput(attrs={
                                             'class': 'form-check-input d-block mt-2',
                                         })
                                         )
    is_percentage = forms.BooleanField(label='Discount Type',
                                       required=False,
                                       widget=forms.CheckboxInput(attrs={
                                           'class': 'd-block form-field-w-100',
                                           'data-toggle': 'toggle',
                                           'data-on': 'Percentage',
                                           'data-off': 'Amount',
                                           'data-onstyle': 'primary',
                                           'data-offstyle': 'primary',
                                       }))

    discount_amount_old = forms.DecimalField(required=False,
                                           widget=widgets.NumberInput(attrs={
                                               'class': 'form-control',
                                               'disabled': 'disabled'
                                           }))

    band_discount_amount = forms.DecimalField(required=False,
                                            widget=widgets.NumberInput(
                                                attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step',
                                                       'placeholder': 'Disc. Amount'}))

    discount_percentage_old = forms.DecimalField(required=False,
                                               widget=widgets.NumberInput(attrs={
                                                   'class': 'form-control',
                                                   'disabled': 'disabled'
                                               }))

    band_discount_percentage = forms.DecimalField(required=False,
                                                widget=widgets.NumberInput(
                                                    attrs={'step': 0.0001, 'max': 100,
                                                           'class': 'form-control auto-round-to-step',
                                                           'placeholder': 'Disc. Percentage'}))

    specific_hookup_method = forms.ModelChoiceField(
        empty_label='All',
        label='Hookup Method',
        queryset=HookupMethod.objects.all(),
        widget=HookupMethodPickWidget(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        self.agreement = kwargs.pop('agreement', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        super().__init__(*args, **kwargs)

        self.fields['inclusive_taxes'].choices = [('A', 'All Applicable Taxes')] + list(
            TaxCategory.objects.order_by('name').values_list('pk', 'name'))

        self.fields['pricing_discount_amount'].label = 'Discount Amount'
        self.fields['pricing_discount_percentage'].label = 'Discount Percentage'
        self.fields['band_discount_amount'].label = 'Discount Amount'
        self.fields['band_discount_percentage'].label = 'Discount Percentage'

        if self.context == 'Supersede':
            self.fields['location'].widget = widgets.Select(attrs={
                'class': 'form-control form-field-w-100',
            })
            self.fields['location'].queryset = Organisation.objects.filter(
                pk=self.instance.location.pk)
            self.fields['location'].label_from_instance = self.location_label_from_instance
            self.fields['location'].disabled = True
            self.fields['inclusive_taxes'].initial, self.fields['cascade_to_fees'].initial = \
                self.instance.inclusive_taxes

            self.fields['ipa'].disabled = True
            self.fields['ipa'].queryset = Organisation.objects.filter(
                pk=getattr(self.instance.ipa, 'pk', None))
            self.fields['ipa'].help_text = self.instance.ipa.details.registered_name \
                if self.instance.ipa else 'TBC / Confirmed on Order'
            self.fields['ipa'].label_from_instance = self.ipa_label_from_instance

        elif self.context == 'Edit':
            self.fields['location'].initial = self.entry.location
            self.fields['location'].disabled = True

            ipas_qs = self.fields['ipa'].queryset
            pricing_location = self.entry.location

            self.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                queryset=ipas_qs.filter(ipa_locations=pricing_location),
                # dependent_fields={'location': 'ipa_locations_here'},
                airport_location=pricing_location, attrs={
                    'class': 'form-control',
                    'data-placeholder': 'Select an Into-Plane Agent'
                })

        if self.instance.band_start is not None:
            if self.instance.pricing_discount_amount is not None:
                self.fields['band_discount_amount'].initial = normalize_fraction(self.instance.pricing_discount_amount)

            if self.instance.pricing_discount_percentage is not None:
                formatted_percentage = self.instance.pricing_discount_percentage.normalize()
                self.fields['band_discount_percentage'].initial = "{:f}".format(formatted_percentage)

        self.fields['fuel'].queryset = FuelType.objects.with_custom_ordering()

        self.fields['ipa'].error_messages['invalid_choice'] = "This Organisation already exists but can't be selected."

        self.fields['destination_type'].queryset = GeographichFlightType.objects.filter(code__in=['ALL', 'INT', 'DOM'])

        self.fields['pricing_discount_unit'].label_from_instance = self.discount_unit_label_from_instance

        self.fields['band_uom'].queryset = UnitOfMeasurement.objects.fluid_with_custom_ordering()
        self.fields['band_uom'].label_from_instance = self.band_unit_label_from_instance

    @staticmethod
    def ipa_label_from_instance(obj):
        return f'{obj.details.registered_name}'

    @staticmethod
    def location_label_from_instance(obj):
        return f'{obj.airport_details.icao_iata}'

    @staticmethod
    def discount_unit_label_from_instance(obj):
        return f'{obj.description}'

    @staticmethod
    def band_unit_label_from_instance(obj):
        return f'{obj.description_plural}'

    class Meta:
        model = FuelAgreementPricingManual
        fields = ['location', 'ipa', 'delivery_methods', 'fuel', 'pricing_discount_unit', 'is_percentage',
                  'pricing_discount_percentage', 'pricing_discount_amount', 'flight_type', 'destination_type',
                  'band_uom', 'band_start', 'band_end', 'band_discount_amount', 'band_discount_percentage', 'comment',
                  'discount_amount_old', 'discount_percentage_old', 'applies_to_private', 'applies_to_commercial',
                  'inclusive_taxes', 'cascade_to_fees', 'client', 'specific_handler', 'specific_apron',
                  'specific_hookup_method']

        widgets = {
            'location': AirportPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Location',
                'icao_iata_label': True,
        }),
            'applies_to_private': widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            'applies_to_commercial': widgets.CheckboxInput(attrs={
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
            'pricing_discount_unit': FuelQuantityPricingUnitPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Pricing Discount Unit',
            }),
            'pricing_discount_amount': widgets.NumberInput(attrs={
                'class': 'form-control set-width auto-round-to-step',
                'placeholder': 'Disc. Amount',
            }),
            'pricing_discount_percentage': widgets.NumberInput(attrs={
                'class': 'form-control set-width auto-round-to-step',
                'placeholder': 'Disc. Percentage',
                'step': 0.0001,
                'max': 100,
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
                'data-placeholder': 'Select Fluid Band Type',
                'data-allow-clear': 'true',
            }),
            'band_start': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1,
                'placeholder': 'Band Start',
            }),
            'band_end': widgets.NumberInput(attrs={
                'class': 'form-control band-width auto-round-to-step',
                'step': 1,
                'placeholder': 'Band End',
            }),
            'comment': widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }

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


class BaseFuelAgreementPricingDiscountFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.agreement = kwargs.pop('agreement', None)
        self.old_agreement = kwargs.pop('old_agreement', None)
        self.extra_fields = kwargs.pop('extra_fields', None)
        self.context = kwargs.pop('context', None)
        self.entry = kwargs.pop('entry', None)
        self.related_entries = kwargs.pop('related_entries', None)
        super().__init__(*args, **kwargs)

        if self.context == 'Supersede':
            self.queryset = FuelAgreementPricingManual.objects.filter(
                parent_entry=None, agreement=self.old_agreement)

            for form in self.forms:
                form.fields['is_percentage'].initial = form['pricing_discount_amount'].initial is None
                form['discount_amount_old'].initial = normalize_fraction(form["pricing_discount_amount"].initial)
                form['pricing_discount_amount'].initial = ''
                form['discount_percentage_old'].initial = normalize_fraction(
                    form["pricing_discount_percentage"].initial)
                form['pricing_discount_percentage'].initial = ''
                form.fields['applies_to_private'].widget.attrs['class'] = 'form-check-input'
                form.fields['applies_to_commercial'].widget.attrs['class'] = 'form-check-input'

                form['band_start'].initial = normalize_fraction(form['band_start'].initial)
                form['band_end'].initial = normalize_fraction(form['band_end'].initial)

        elif self.context == 'Edit':
            self.queryset = FuelAgreementPricingManual.objects.filter(id=self.entry.pk)

            self.forms[0]['band_start'].initial = normalize_fraction(self.forms[0]['band_start'].initial)
            self.forms[0]['band_end'].initial = normalize_fraction(self.forms[0]['band_end'].initial)

            for form in self.forms:
                form['pricing_discount_amount'].initial = normalize_fraction(form['pricing_discount_amount'].initial)
                form['pricing_discount_percentage'].initial = normalize_fraction(form['pricing_discount_percentage'].initial)

                form.fields['is_percentage'].initial = self.entry.is_percentage
                form['inclusive_taxes'].initial, form['cascade_to_fees'].initial = self.entry.inclusive_taxes

        # On creation
        else:
            self.queryset = FuelAgreementPricingManual.objects.none()

            for value, form in enumerate(self.forms):
                form.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
                    dependent_fields={f'new-pricing-{value}-location': 'ipa_locations'},
                    context='formset', form_name=f'new-pricing-{value}', attrs={
                        'class': 'form-control',
                        'data-placeholder': 'Select an Into-Plane Agent'
                    })

        # Register dependent fields
        prefix = 'existing-discount-pricing' if self.context == 'Supersede' else 'new-pricing'

        for value, form in enumerate(self.forms):
            form.fields['specific_handler'].widget = HandlerPickWidget(
                queryset=Organisation.objects.handling_agent(),
                dependent_fields={
                    f'{prefix}-{value}-location': 'handler_details__airport'},
                attrs={'class': 'form-control'}
            )

        if len(self.forms) > 0:
            self.forms[0].empty_permitted = False

        for form in self.forms:
            form.fields['pricing_discount_unit'].required = form.fields['is_percentage']

    def add_fields(self, form, index):
        super(BaseFuelAgreementPricingDiscountFormSet, self).add_fields(form, index)
        related_entries = FuelAgreementPricingManual.objects\
            .filter(parent_entry=form['id'].initial) \
            .order_by('band_start')

        if self.context == 'Supersede':
            classes = 'form-control band-width'
        else:
            classes = 'form-control'

        if self.extra_fields:
            for form_number, value in self.extra_fields.items():
                for value in range(int(value)):
                    if index == form_number:
                        form.fields[f'band_start-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}',
                                                                                 'placeholder': 'Band Start'}))

                        form.fields[f'band_end-additional-{form_number}-{value + 1}'] = \
                            forms.IntegerField(required=False,
                                               widget=widgets.NumberInput(attrs={'class': f'{classes}',
                                                                                 'placeholder': 'Band End'}))

                        if self.context == 'Supersede':
                            if value < related_entries.count():
                                form.fields[f'discount_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                                       'disabled': 'disabled'}))
                                form.fields[f'discount_percentage_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control',
                                                                                       'disabled': 'disabled'}))
                            else:
                                form.fields[f'discount_amount_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                                       'disabled': 'disabled'}))
                                form.fields[f'discount_percentage_old-additional-{form_number}-{value + 1}'] = \
                                    forms.DecimalField(required=False,
                                                     widget=widgets.NumberInput(attrs={'class': 'form-control d-none',
                                                                                       'disabled': 'disabled'}))

                        form.fields[f'band_discount_amount-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step',
                                                        'placeholder': 'Disc. Amount', }))

                        form.fields[f'band_discount_percentage-additional-{form_number}-{value + 1}'] = \
                            forms.DecimalField(required=True,
                                             widget=widgets.NumberInput(
                                                 attrs={'step': 0.0001, 'class': 'form-control auto-round-to-step',
                                                        'placeholder': 'Disc. Percentage', }))

        elif self.related_entries or self.context == 'Supersede':
            form_number = index
            for value, entry in enumerate(related_entries):

                form.fields[f'band_start-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.band_start),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step',
                                                                         'placeholder': 'Band Start'}))

                form.fields[f'band_end-additional-{form_number}-{value + 1}'] = \
                    forms.IntegerField(required=False, initial=normalize_fraction(entry.band_end),
                                       widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                         'class': f'{classes} auto-round-to-step',
                                                                         'placeholder': 'Band End'}))

                if self.context == 'Supersede':
                    form.fields[f'discount_amount_old-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(entry.pricing_discount_amount),
                                         widget=widgets.NumberInput(
                                             attrs={'step': 0.0001, 'class': 'form-control', 'disabled': 'disabled'}))
                    form.fields[f'discount_percentage_old-additional-{form_number}-{value + 1}'] = \
                        forms.DecimalField(required=False, initial=normalize_fraction(entry.pricing_discount_percentage),
                                         widget=widgets.NumberInput(
                                             attrs={'step': 0.0001, 'class': 'form-control', 'disabled': 'disabled'}))

                form.fields[f'band_discount_amount-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(
                        entry.pricing_discount_amount) if self.context != 'Supersede' else '',
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step',
                                                                       'placeholder': 'Disc. Amount', }))

                form.fields[f'band_discount_percentage-additional-{form_number}-{value + 1}'] = \
                    forms.DecimalField(required=True, initial=normalize_fraction(
                        entry.pricing_discount_percentage) if self.context != 'Supersede' else '',
                                     widget=widgets.NumberInput(attrs={'step': 0.0001,
                                                                       'class': 'form-control auto-round-to-step',
                                                                       'placeholder': 'Disc. Percentage', }))

    def clean(self):
        # Get other supplier agreements to check for overlaps
        supplier_agreements = FuelAgreement.objects \
            .filter(Q(supplier=self.agreement.supplier) & ~Q(pk=self.agreement.pk)) \
            .prefetch_related('pricing_formulae', 'pricing_manual')

        for form_number, form in enumerate(self.forms):
            data = form.cleaned_data
            location = form.cleaned_data.get('location')

            if location:
                ipa = data.get('ipa')
                overlap_msg = pricing_check_overlap(location, ipa, self.agreement, supplier_agreements)

                if overlap_msg:
                    form.add_error(None, forms.ValidationError(overlap_msg))

            # 'All' here is an empty label only, so we need to remove error (there are alternative solutions, this one
            # is the most painless)
            if form.cleaned_data.get('specific_hookup_method') is None:
                form.errors.pop('specific_hookup_method', None)

            if not data.get('DELETED'):
                if data.get('is_percentage'):
                    form._errors.pop('pricing_discount_unit', None)
                    form._errors.pop('pricing_discount_amount', None)
                    form._errors.pop('band_discount_amount', None)

                    if data.get('pricing_discount_percentage') is None and \
                        data.get('band_discount_percentage') is not None:
                        form._errors.pop('pricing_discount_percentage', None)

                    elif data.get('pricing_discount_percentage') is None and \
                        data.get('band_discount_percentage') is None and \
                        data.get('band_uom') is not None:

                        form.add_error('band_discount_percentage', 'This field is required')
                        form._errors.pop('pricing_discount_percentage', None)
                else:
                    form._errors.pop('pricing_discount_percentage', None)
                    form._errors.pop('band_discount_percentage', None)

                    if data.get('pricing_discount_amount') is None and data.get('band_discount_amount') is not None:
                        form._errors.pop('pricing_discount_amount', None)

                    elif data.get('pricing_discount_amount') is None and \
                        data.get('band_discount_amount') is None and \
                        data.get('band_uom') is not None:

                        form.add_error('band_discount_amount', 'This field is required')
                        form._errors.pop('pricing_discount_amount', None)

            if form.has_changed():
                if not data.get('applies_to_private') and \
                    not data.get('applies_to_commercial'):
                    form.add_error('applies_to_private', 'One of the checkboxes needs to be checked')
                    form.add_error('applies_to_commercial', '')

            instances_of_band_1 = 0
            has_band_pricing = False
            for field, value in data.items():
                if 'band_start' in field and value is not None:
                    has_band_pricing = True
                    instances_of_band_1 += 1

            cleaned_data_copy = data.copy()

            if has_band_pricing:
                discount_type = 'discount_percentage' if data.get('is_percentage') else 'discount_amount'
                other_type = 'discount_amount' if data.get('is_percentage') else 'discount_percentage'

                form._errors = {field: val for field, val in form._errors.items() if other_type not in field}

                if data.get('band_uom') is None and instances_of_band_1 != 0:
                    form.add_error('band_uom',
                                   'This field is required when band pricing or multiple band rows are present')

                if data.get('band_uom') is not None:
                    validate_band_rows(cleaned_data_copy, form, form_number, 'band', 'integer')

                for field, value in cleaned_data_copy.items():
                    if self.context == 'Supersede':
                        if f'band_{discount_type}-additional' in field and value is None:
                            form.add_error(field, '')
                    else:
                        if f'band_{discount_type}' in field and value is None:
                            form.add_error(field, '')

            if data.get('DELETE'):
                for error in list(form.errors):
                    del form.errors[error]

        self.validate_unique()


FuelAgreementPricingDiscountFormset = modelformset_factory(FuelAgreementPricingManual,
                                                          can_delete=True,
                                                          extra=0,
                                                          form=FuelAgreementPricingDiscountPricingForm,
                                                          formset=BaseFuelAgreementPricingDiscountFormSet
                                                          )

NewFuelAgreementPricingDiscountFormset = modelformset_factory(FuelAgreementPricingManual,
                                                             extra=30,
                                                             can_delete=True,
                                                             form=FuelAgreementPricingDiscountPricingForm,
                                                             formset=BaseFuelAgreementPricingDiscountFormSet
                                                             )
