import pytz
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms

from handling.form_widgets import HandlingRequestLocationPickWidget
from handling.models import HandlingRequestMovement
from handling.utils.localtime import get_utc_from_airport_local_time
from handling.utils.validators import validate_handling_request_for_duplicate_v2
from organisation.models import Organisation


class HandlingRequestUpdatePPRForm(BSModalForm):
    arrival_ppr_number = HandlingRequestMovement.ppr_number.field.formfield(
        label='Arrival PPR Number',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )
    departure_ppr_number = HandlingRequestMovement.ppr_number.field.formfield(
        label='Departure PPR Number',
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request', None)
        super().__init__(*args, **kwargs)

        arrival_ppr_number = getattr(self.handling_request.arrival_movement, 'ppr_number', None)
        departure_ppr_number = getattr(self.handling_request.departure_movement, 'ppr_number', None)
        self.fields['arrival_ppr_number'].initial = arrival_ppr_number
        self.fields['departure_ppr_number'].initial = departure_ppr_number


class HandlingRequestUpdateMovementDetailsForm(BSModalModelForm):
    IS_LOCAL_TIME_CHOICES = (
        (False, _("UTC")),
        (True, _("Local"))
    )

    new_date = forms.DateTimeField(
        label='Date',
        required=False,
        widget=widgets.DateTimeInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
        }))
    new_time = forms.TimeField(
        label='Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )
    is_local_timezone = forms.TypedChoiceField(
        label='Timezone',
        initial=False,
        coerce=lambda x: x == 'True',
        choices=IS_LOCAL_TIME_CHOICES,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_date'].initial = self.instance.date.date()
        self.fields['new_time'].initial = self.instance.date.time().strftime("%H:%M")

        if self.instance.pk:
            self.fields['airport'].queryset = Organisation.objects.handling_request_locations()
            if self.instance.direction_id == 'ARRIVAL':
                self.fields['airport'].label = 'Arrival From Airport'
            if self.instance.direction_id == 'DEPARTURE':
                self.fields['airport'].label = 'Departure To Airport'

        handling_request = getattr(self.instance, 'request')

        if not handling_request.airport.is_lat_lon_available:
            self.fields['is_local_timezone'].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        # Combine date and time into datetime
        date = cleaned_data['new_date']
        time = cleaned_data['new_time']
        submitted_date = date.combine(date, time).replace(tzinfo=None)
        self.instance.date = submitted_date

        handling_request = getattr(self.instance, 'request')
        is_datetime_local = self.cleaned_data['is_local_timezone']

        if is_datetime_local:
            submitted_date = get_utc_from_airport_local_time(local_datetime=self.instance.date,
                                                             organisation=handling_request.airport)

        if self.instance.direction.code == 'ARRIVAL':
            arrival_date = submitted_date
            if arrival_date.tzinfo is None:
                arrival_date = pytz.utc.localize(arrival_date)
            departure_date = handling_request.departure_movement.date
        else:
            arrival_date = handling_request.arrival_movement.date
            departure_date = submitted_date
            if departure_date.tzinfo is None:
                departure_date = pytz.utc.localize(departure_date)

        if departure_date < timezone.now():
            self.add_error(None, ValidationError("Date & time can't be in the past"))

        # Validate departure over arrival datetime
        if departure_date <= arrival_date:
            departure_earlier_than_arrival_msg = 'Departure cannot be earlier than Arrival'
            self.add_error(None, ValidationError(departure_earlier_than_arrival_msg))

        # Validate for duplicate
        duplicate_request = validate_handling_request_for_duplicate_v2(
            organisation_id=handling_request.customer_organisation.pk,
            callsign=handling_request.callsign,
            arrival_date=arrival_date,
            departure_date=departure_date,
            tail_number_id=handling_request.tail_number.pk if handling_request.tail_number else None,
            airport_id=handling_request.airport.pk,
            mission_number=handling_request.mission_number,
            exclude_id=handling_request.pk,
        )

        if duplicate_request:
            duplicate_request_url = ''
            if self.request.app_mode == 'ops_portal':
                duplicate_request_url = reverse_lazy('admin:handling_request', kwargs={'pk': duplicate_request.pk})
            if self.request.app_mode == 'dod_portal':
                duplicate_request_url = reverse_lazy('dod:request', kwargs={'pk': duplicate_request.pk})

            self.add_error(
                field=None,
                error=ValidationError(
                    'This Servicing & Fueling Request conflicts with an existing request - '
                    '<a href="{url}">{callsign}</a>'.format(
                        url=duplicate_request_url,
                        callsign=duplicate_request.callsign,
                    )))

        return cleaned_data

    class Meta:
        model = HandlingRequestMovement
        fields = [
            'new_date', 'new_time',
            'airport',
            'crew',
            'is_passengers_onboard',
            'is_passengers_tbc',
            'passengers',
        ]
        widgets = {
            "airport": HandlingRequestLocationPickWidget(attrs={
                'class': 'form-control'
            }),
            "crew": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "is_passengers_onboard": widgets.CheckboxInput(attrs={
                'class': 'd-block m-3',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'danger',
            }),
            "passengers_tbc": widgets.CheckboxInput(attrs={
                'class': 'form-check-input mt-0'
            }),
            "passengers": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
        }

    def save(self, commit=True):
        request_person = getattr(self.request.user, 'person', None)
        instance = super().save(commit=False)
        instance.updated_by = request_person
        instance.is_datetime_local = self.cleaned_data['is_local_timezone']

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            instance = super().save(commit=commit)
        return instance
