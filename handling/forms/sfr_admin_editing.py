from django import forms
from django.forms import widgets
from bootstrap_modal_forms.forms import BSModalForm
from django_flatpickr.schemas import FlatpickrOptions
from django_flatpickr.widgets import DateTimePickerInput
from django_select2 import forms as s2forms

from handling.models import HandlingRequestMovement

flatpickr_options = FlatpickrOptions(
    static=False,
    allowInput=False,
)


class HandlingRequestAdminEditingForm(BSModalForm):
    arrival_date = HandlingRequestMovement._meta.get_field('date').formfield(
        label='Arrival Date',
        required=True,
        widget=DateTimePickerInput(
            options=flatpickr_options,
            attrs={
                'class': 'form-control',
            }),
    )

    arrival_is_local_timezone = forms.TypedChoiceField(
        label='Timezone',
        required=False,
        initial=False,
        coerce=lambda x: x == 'True',
        choices=HandlingRequestMovement.IS_LOCAL_TIME_CHOICES,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )
    departure_date = HandlingRequestMovement._meta.get_field('date').formfield(
        label='Departure Date',
        required=True,
        widget=DateTimePickerInput(
            options=flatpickr_options,
            attrs={
                'class': 'form-control',
            }),
    )

    departure_is_local_timezone = forms.TypedChoiceField(
        label='Timezone',
        required=False,
        initial=False,
        coerce=lambda x: x == 'True',
        choices=HandlingRequestMovement.IS_LOCAL_TIME_CHOICES,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )

    retain_fuel_order = forms.BooleanField(
        label='Retain existing fuel order?',
        required=False,
        initial=True,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    confirm_ground_handling = forms.BooleanField(
        label='Confirm Ground Handling?',
        required=False,
        initial=True,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    confirm_all_services = forms.BooleanField(
        label='Confirm all Outstanding Services?',
        required=False,
        initial=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request', None)
        super().__init__(*args, **kwargs)
        self.fields['arrival_date'].initial = self.handling_request.arrival_movement.date
        self.fields['departure_date'].initial = self.handling_request.departure_movement.date

        # Disable 'Confirm Ground Handling?' in case if Handler is not selected for the S&F Request
        if not self.handling_request.handling_agent:
            self.fields['confirm_ground_handling'].initial = False
            self.fields['confirm_ground_handling'].disabled = True
            self.fields['confirm_ground_handling'].help_text = ("Not available due to Ground Handler "
                                                                "has not been selected.")
