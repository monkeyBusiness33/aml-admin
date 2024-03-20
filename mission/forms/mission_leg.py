from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django_flatpickr.schemas import FlatpickrOptions
from django_flatpickr.widgets import DateTimePickerInput, DatePickerInput, TimePickerInput

from core.form_widgets import flatpickr_time_input_options
from handling.form_widgets import OrganisationAircraftTypeDependedPickWidget, HandlingRequestLocationPickWidget
from mission.forms._form_widgets import MissionTailNumberDependedPickWidget
from mission.models import MissionLeg
from organisation.models import Organisation


class MissionLegQuickEditForm(BSModalModelForm):
    time_en_route = forms.CharField(
        label='Estimated Time En-Route',
        required=False,
        widget=widgets.TextInput(attrs={
            'class': 'form-control duration-picker',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leg_prev = self.instance.get_prev_leg()
        self.leg_next = self.instance.get_next_leg()

        # Departure datetime options
        departure_datetime_options = FlatpickrOptions(
            minDate=self.leg_prev.arrival_datetime.strftime('%Y-%m-%d %H:%M') if self.leg_prev else '',
            maxDate=self.leg_next.departure_datetime.strftime('%Y-%m-%d %H:%M') if self.leg_next else ''
        )
        self.fields['departure_datetime'].widget = DateTimePickerInput(
            attrs={'class': 'form-control'},
            options=departure_datetime_options,
        )

        # Arrival datetime options
        arrival_datetime_options = FlatpickrOptions(
            minDate=self.leg_prev.arrival_datetime.strftime('%Y-%m-%d %H:%M') if self.leg_prev else '',
            maxDate=self.leg_next.departure_datetime.strftime('%Y-%m-%d %H:%M') if self.leg_next else '',
        )
        self.fields['arrival_datetime'].widget = DateTimePickerInput(
            attrs={'class': 'form-control'},
            options=arrival_datetime_options,
        )

    def clean(self):
        cleaned_data = super().clean()
        departure_datetime = cleaned_data.get('departure_datetime')
        arrival_datetime = cleaned_data.get('arrival_datetime')
        if departure_datetime >= arrival_datetime:
            self.add_error('departure_datetime', ValidationError("Departure can't be greater than Arrival"))

        if self.instance.previous_leg:
            if departure_datetime <= self.instance.previous_leg.arrival_datetime:
                self.add_error('departure_datetime', ValidationError(
                    "Departure can't be earlier than previous Flight Leg - {sequence_id} {leg_repr}".format(
                        sequence_id=self.instance.previous_leg.sequence_id,
                        leg_repr=self.instance.previous_leg,
                    )
                ))

        if self.instance.get_next_leg():
            if arrival_datetime >= self.instance.get_next_leg().departure_datetime:
                self.add_error('arrival_datetime', ValidationError(
                    "Arrival can't be greater than next Flight Leg - {sequence_id} {leg_repr}".format(
                        sequence_id=self.instance.get_next_leg().sequence_id,
                        leg_repr=self.instance.get_next_leg(),
                    )
                ))

    class Meta:
        model = MissionLeg
        fields = [
            'callsign_override',
            'departure_datetime',
            'time_en_route',
            'arrival_datetime',
            'pob_pax',
            'cob_lbs',
            'departure_diplomatic_clearance',
            'arrival_diplomatic_clearance',
        ]
        labels = {
            'callsign_override': "Callsign (override)"
        }

        widgets = {
            "callsign_override": forms.TextInput(attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();this.value = this.value.replace(/\s/g, "");',
            }),
            "departure_datetime": DateTimePickerInput(attrs={
                'class': 'form-control',
            }),
            "departure_diplomatic_clearance": forms.TextInput(attrs={
                'class': 'form-control',
            }),
            "arrival_datetime": forms.TextInput(attrs={
                'class': 'form-control',
            }),
            "arrival_diplomatic_clearance": forms.TextInput(attrs={
                'class': 'form-control',
            }),
            "pob_pax": forms.TextInput(attrs={
                'class': 'form-control',
            }),
            "cob_lbs": forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionLegChangeAircraftForm(BSModalModelForm):
    apply_to_subsequent_legs = forms.BooleanField(
        label="Apply aircraft change to all subsequent flight legs in this mission?",
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mission = self.instance.mission

        aircraft_type_qs = self.fields['aircraft_type_override'].queryset
        self.fields['aircraft_type_override'].queryset = aircraft_type_qs.filter(organisations=mission.organisation)

        self.fields['aircraft_override'].queryset = mission.organisation.get_operable_fleet()

    class Meta:
        model = MissionLeg
        fields = [
            'aircraft_type_override',
            'aircraft_override',
        ]

        widgets = {
            "aircraft_type_override": OrganisationAircraftTypeDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "aircraft_override": MissionTailNumberDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }


class MissionLegCancelForm(BSModalForm):
    prev_arrival_datetime = MissionLeg._meta.get_field('arrival_datetime').formfield()
    next_departure_datetime = MissionLeg._meta.get_field('arrival_datetime').formfield()
    new_location = MissionLeg._meta.get_field('arrival_location').formfield(
        queryset=Organisation.objects.handling_request_locations(),
        widget=HandlingRequestLocationPickWidget(attrs={
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        self.mission_leg = kwargs.pop('mission_leg', None)
        super().__init__(*args, **kwargs)
        leg_prev = self.mission_leg.get_prev_leg()
        leg_next = self.mission_leg.get_next_leg()

        # PREV Arrival Datetime
        if leg_prev:
            self.fields['prev_arrival_datetime'].label = f'"Flight Leg {leg_prev.sequence_id}" Arrival Datetime'
            self.fields['prev_arrival_datetime'].initial = leg_prev.arrival_datetime
            prev_arrival_datetime_opts = FlatpickrOptions(
                minDate=leg_prev.departure_datetime.strftime('%Y-%m-%d %H:%M') if leg_prev else '',
            )
        else:
            self.fields['prev_arrival_datetime'].label = f'No Flight Leg in beginning'
            self.fields['prev_arrival_datetime'].required = False
            self.fields['prev_arrival_datetime'].disabled = True
            prev_arrival_datetime_opts = None

        self.fields['prev_arrival_datetime'].widget = DateTimePickerInput(
            attrs={'class': 'form-control'},
            options=prev_arrival_datetime_opts,
        )

        # NEXT Departure Datetime
        if leg_next:
            self.fields['next_departure_datetime'].label = f'"Flight Leg {leg_next.sequence_id}" Departure Datetime'
            self.fields['next_departure_datetime'].initial = leg_next.departure_datetime
            next_departure_datetime_opts = FlatpickrOptions(
                maxDate=leg_next.arrival_datetime.strftime('%Y-%m-%d %H:%M') if leg_next else '',
            )
        else:
            self.fields['next_departure_datetime'].label = f'No Flight Leg in future'
            self.fields['next_departure_datetime'].required = False
            self.fields['next_departure_datetime'].disabled = True
            next_departure_datetime_opts = None

        self.fields['next_departure_datetime'].widget = DateTimePickerInput(
            attrs={'class': 'form-control'},
            options=next_departure_datetime_opts,
        )

        # Location field opts
        self.fields['new_location'].label = 'Location for {leg_prev_repr}{concatenation}{leg_next_repr}'.format(
            leg_prev_repr=f'"Flight Leg {leg_prev.sequence_id}" Arrival' if leg_prev else '',
            concatenation=' and ' if leg_prev and leg_next else '',
            leg_next_repr=f'"Flight Leg {leg_next.sequence_id}" Departure' if leg_next else '',
        )
        self.fields['new_location'].initial = leg_next.departure_location if leg_next else None


class DailyScheduleForm(forms.Form):
    date = forms.DateField(
        label='Date',
        widget=DatePickerInput(
            options=FlatpickrOptions(
                altFormat='Y-m-d',
            ),
            attrs={'class': 'form-control d-inline-block'},
        )
    )

    def __init__(self, *args, **kwargs):
        self.date = kwargs.pop('date', None)
        super().__init__(*args, **kwargs)
        self.initial['date'] = self.date
