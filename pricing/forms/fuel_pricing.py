import re
from decimal import Decimal
from django import forms
from django.db.models import F
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.forms import BaseFormSet, formset_factory, widgets
from django.forms.models import ModelChoiceField
from django_select2.forms import Select2Widget
from aircraft.forms import AircraftTypePickWidget
from aircraft.form_widgets import AllAircraftRegistrationPickWidget
from aircraft.models import Aircraft, AircraftType
from core.form_widgets import CurrencyPickWidget, FlightTypePickWidget, FuelCategoryPickWidget, UomPickWidget
from core.models import ApronType, Currency, FlightType, FuelCategory, FuelType, UnitOfMeasurement
from core.utils.custom_query_expressions import RegistrationWithoutPunctuation
from pricing.form_widgets import ApronTypePickWidget, ClientPickWidget, HandlerPickWidget
from organisation.form_widgets import AirportPickWidget
from organisation.models import Organisation
from pricing.models import PricingCalculationRecord


class FuelPricingCalculationForm(forms.Form):
    '''
    Form for specifying fuel pricing calculation itinerary
    '''

    def __init__(self, *args, **kwargs):
        self.empty_permitted = False
        self.context = kwargs.pop('context')
        self.airport = kwargs.pop('airport')
        super().__init__(*args, **kwargs)
        self.fields['fuel_type'].initial = FuelType.objects.get(pk=1)
        self.fields['uplift_uom'].initial = UnitOfMeasurement.objects.get(code='L')
        self.fields['is_international'].initial = True
        self.fields['currency'].initial = Currency.objects.get(code='USD')
        self.fields['overwing_fueling'].initial = True

        # On airport pages, the location field can't be required
        if self.context == 'Airport':
            self.fields['location'].initial = self.airport
            self.fields['location'].disabled = True

        # Override queryset for form instance on airport page (Need to recreate the widget,
        # otherwise forms for other airports in other tabs are affected, as the ID remains the same).
        # For the airport-agnostic page, make the field dependent on location field
        if self.context == 'Airport':
            self.fields['handler'].widget = HandlerPickWidget(
                queryset=Organisation.objects.handling_agent().filter(
                    handler_details__airport=self.airport),
                attrs={'class': 'form-control'}
            )
        else:
            self.fields['handler'].widget = HandlerPickWidget(
                queryset=Organisation.objects.handling_agent(),
                dependent_fields={f'{self.prefix}-location': 'handler_details__airport'},
                attrs={'class': 'form-control'}
            )


    def clean_is_private(self):
        flight_type = self.cleaned_data.get('flight_type')
        is_private = self.cleaned_data.get('is_private')

        if flight_type.code in ['M', 'T'] and not is_private:
            label = re.sub('(.+Flight).*', r'\1', flight_type.name)
            raise ValidationError(f'{label}s are always considered private')

        return is_private

    def clean(self):
        data = self.cleaned_data

        # Uplift quantity and uom are required for calculation, but only if fuel uplift actually occurs
        if data['is_fuel_taken']:
            if data['uplift_qty'] is None:
                self.add_error('uplift_qty', 'This field is required')

            if data['uplift_uom'] is None:
                self.add_error('uplift_uom', 'This field is required')

        if 'src_calculation_id' in data:
            # Check if the source calculation exists and matches the form params
            src_calculation_id = data['src_calculation_id']

            try:
                src_calculation = PricingCalculationRecord.objects.get(pk=src_calculation_id)
                params = src_calculation.scenario
                assert (Decimal(params['uplift_qty']) == data['uplift_qty'])
                assert (params['uplift_uom'].get('pk', None) == data['uplift_uom'].pk)
                assert (params['fuel_cat'].get('pk', None) == data['fuel_type'].pk)
                assert (params['currency'].get('pk', None) == data['currency'].pk)
                assert (params['flight_type'].get('code', None) == data['flight_type'].code)

                if params.get('aircraft', None):
                    assert (params['aircraft'].get('pk', None) == data['aircraft'].pk)

                if params.get('aircraft_type', None):
                    assert (params['aircraft_type'].get('pk', None) == data['aircraft_type'].pk)

                assert (params['is_private'] == data['is_private'])
                assert (params['is_international'] == data['is_international'])
            except (ObjectDoesNotExist, AssertionError) as e:
                self.errors['src_calculation_id'] = [f"The original calculation results could not be found"
                                                     f" or their input parameters do not match the parameters"
                                                     f" in the Pricing Scenario form {e}"]

    fuel_type = ModelChoiceField(
        label='Fuel Type',
        queryset=FuelCategory.objects.all(),
        widget=FuelCategoryPickWidget(
            attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }
        ),
    )

    uplift_qty = forms.DecimalField(
        label='Uplift Quantity',
        required=False,
        initial=0,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control extend-label form-field-w-50 auto-round-to-step',
                'min': 0, 'step': 0.0001
            }
        ),
    )

    uplift_uom = ModelChoiceField(
        required=False,
        queryset=UnitOfMeasurement.objects.fluid_with_custom_ordering(),
        widget=UomPickWidget(
            attrs={
                'data-minimum-input-length': 0,
                'class': 'form-control no-label form-field-w-50 ps-2',
            }
        ),
    )

    uplift_datetime = forms.DateTimeField(
        label='Uplift Date & Time',
        required=False,
        widget=widgets.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                'type': 'datetime-local',
                'class': 'form-control extend-label form-field-w-60',
            }
        ),
    )

    uplift_time_type = forms.ChoiceField(
        choices=[('L', 'Local'), ('U', 'UTC')],
        initial='L',
        required=False,
        widget=Select2Widget(
            attrs={
                'class': 'form-control no-label form-field-w-40',
                'data-allow-clear': 'false',
            }
        ),
    )

    is_international = forms.BooleanField(
        label='Destination of Flight',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100',
                'data-toggle': 'toggle',
                'data-on': 'International',
                'data-off': 'Domestic',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
    )

    flight_type = ModelChoiceField(
        required=True,
        queryset=FlightType.objects.exclude(pk='A'),
        label='Flight Type',
        widget=FlightTypePickWidget(
            attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
                'data-placeholder': 'Select Flight Type',
            }
        ),
    )

    is_private = forms.BooleanField(
        label='Commercial / Private',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100',
                'data-toggle': 'toggle',
                'data-on': 'Private',
                'data-off': 'Commercial',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
    )

    currency = ModelChoiceField(
        queryset=Currency.objects.all(),
        label='Currency',
        required=False,
        widget=CurrencyPickWidget(
            attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Currency',
            }
        ),
    )

    aircraft = ModelChoiceField(
        queryset=Aircraft.objects.annotate(
            registration_without_punctuation=RegistrationWithoutPunctuation(F('details__registration'))
        ).order_by('details__registration').all(),
        label='Aircraft',
        required=False,
        widget=AllAircraftRegistrationPickWidget(
            attrs={
                'class': 'form-control',
                'data-allow-clear': 'true',
                'data-placeholder': 'Select Aircraft',
            }
        ),
    )

    aircraft_type = ModelChoiceField(
        queryset=AircraftType.objects.all(),
        label='Aircraft Type',
        required=False,
        widget=AircraftTypePickWidget(
            attrs={
                'class': 'form-control',
                'data-allow-clear': 'true',
                'data-placeholder': 'Select Aircraft Type',
            }
        ),
    )

    override_xr = forms.BooleanField(
        label='Override Exchange Rates?',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'primary',
            }),
    )

    specific_client = forms.ModelChoiceField(
        label='Specific Client',
        required=False,
        queryset=Organisation.objects.all(),
        widget=ClientPickWidget(
            attrs={
                'class': 'form-control',
            }),
    )

    handler = forms.ModelChoiceField(
        label='Specific Ground Handler',
        required=False,
        queryset=Organisation.objects.handling_agent(),
        widget=HandlerPickWidget(
            attrs={
                'class': 'form-control',
            }),
    )

    apron = forms.ModelChoiceField(
        label='Uplift Apron',
        required=False,
        queryset=ApronType.objects.all(),
        widget=ApronTypePickWidget(
            attrs={
                'class': 'form-control',
            }),
    )

    overwing_fueling = forms.BooleanField(
        label='Fueling Method',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-field-w-100 toggle-label-ellipsis',
                'data-toggle': 'toggle',
                'data-on': 'Over-Wing Fueling',
                'data-off': 'Single-Point Pressure Fueling',
                'data-onstyle': 'primary',
                'data-offstyle': 'primary',
            }),
    )

    location = forms.ModelChoiceField(
        label='Location',
        required=True,
        queryset=Organisation.objects.airport(),
        widget=AirportPickWidget(
            attrs={
                'class': 'form-control',
                'required': 'required',
                'data-placeholder': 'Select Airport',
            }),
    )

    # Advanced Options

    is_fuel_taken = forms.BooleanField(
        label='Fuel Taken?',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-check-input',
            }),
    )

    is_defueling = forms.BooleanField(
        label='Defueling Service?',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-check-input',
            }),
    )

    is_multi_vehicle = forms.BooleanField(
        label='Multi-Vehicle Uplift?',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-check-input',
            }),
    )

    extend_expired_agreement_client_pricing = forms.BooleanField(
        label='Extend Expired Agreement / Client-Specific Pricing? <i class ="ms-1 fa fa-info-circle" '
              'data-bs-toggle="tooltip" data-bs-placement="top" data-bs-original-title="If this option is checked,'
              ' any expired agreement-based or client-specific pricing will be extended. Otherwise, it is assumed'
              ' that these are not applicable beyond their expiration dates."></i>',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block form-check-input extend-label',
            }),
    )


class BaseFuelPricingCalculationFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.airport = kwargs.pop('airport', None)

        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        pass


FuelPricingCalculationFormSet = formset_factory(form=FuelPricingCalculationForm,
                                                formset=BaseFuelPricingCalculationFormSet)
