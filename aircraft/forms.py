from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.db import transaction
from django.forms import widgets
from bootstrap_modal_forms.forms import BSModalModelForm
from django_select2 import forms as s2forms

from aircraft.models import AircraftType, AircraftHistory, Aircraft
from aircraft.utils.registration_duplicate_finder import validate_aircraft_registration
from organisation.form_widgets import AirportPickWidget

from core.form_widgets import CountryPickWidget
from organisation.models.organisation import Organisation


class AircraftTypesPickWidget(s2forms.ModelSelect2MultipleWidget):
    model = AircraftType
    search_fields = [
        "manufacturer__icontains",
        "model__icontains",
        "designator__icontains",
    ]


class AircraftTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "manufacturer__icontains",
        "model__icontains",
        "designator__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.manufacturer} {obj.model} ({obj.designator})')


class AircraftForm(BSModalModelForm):

    registration = AircraftHistory.registration.field.formfield(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();',
                }),
    )

    homebase = AircraftHistory.homebase.field.formfield(
        widget=AirportPickWidget(
            attrs={'class': 'form-control'}),
    )

    registered_country = AircraftHistory.registered_country.field.formfield(
        widget=CountryPickWidget(
            attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        self.fields['homebase'].empty_label = 'Select Homebase'

        if hasattr(self.instance.details, 'pk'):
            aircraft_details = self.instance.details
            self.fields['registration'].initial = aircraft_details.registration
            self.fields['homebase'].initial = aircraft_details.homebase
            self.organisation = Organisation.objects.get(pk=aircraft_details.operator_id)
            self.fields['registered_country'].initial = aircraft_details.registered_country
        else:
            self.fields['registered_country'].initial = self.organisation.details.country.id

        if self.instance.pk:
            self.fields['type'].disabled = True

        # DoD User restrictions
        dod_selected_position = getattr(
            self.request, 'dod_selected_position', None)
        if dod_selected_position:
            self.fields['type'].queryset = dod_selected_position.organisation.aircraft_types

    class Meta:
        model = Aircraft
        fields = [
            'registration',
            'registered_country',
            'type',
            'pax_seats',
            'homebase',
        ]

        widgets = {
            'type': AircraftTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'data-placeholder': 'Select Aircraft Type',
            }),
            'yom': widgets.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 4,
                'max': 2100,
            }),
            'pax_seats': widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
        }

    def clean_registration(self):
        registration = self.cleaned_data['registration']
        registration = validate_aircraft_registration(registration, self.instance)
        return registration

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def save(self, commit=True):
        aircraft = super().save(commit=False)
        if hasattr(aircraft.details, 'pk'):
            aircraft_details = aircraft.details
        else:
            aircraft_details = AircraftHistory()

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():
                    aircraft.save()

                    aircraft_details.aircraft = aircraft
                    aircraft_details.registration = self.cleaned_data['registration']
                    if self.organisation:
                        aircraft_details.operator = self.organisation
                    aircraft_details.registered_country = self.cleaned_data['registered_country']
                    aircraft_details.homebase = self.cleaned_data['homebase']
                    aircraft_details.save()

                    self._save_m2m()

                    if aircraft_details.operator.is_military:
                        aircraft_details.operator.aircraft_types.add(aircraft.type, through_defaults={})
            else:
                self.save_m2m = self._save_m2m
        return aircraft
