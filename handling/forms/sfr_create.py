from datetime import datetime, timedelta

import pytz
from bootstrap_modal_forms.mixins import PopRequestMixin
from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.forms import widgets
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_flatpickr.schemas import FlatpickrOptions
from django_flatpickr.widgets import DatePickerInput
from django_select2 import forms as s2forms

from aircraft.models import AircraftHistory
from core.custom_form_fields import WeekdayFormField
from core.form_widgets import UomPickWidget
from handling.form_widgets import HandlingRequestLocationPickWidget, PreferredGroundHandlingPickWidget, \
    HandlingRequestTypePickWidget, OrganisationAircraftTypeDependedPickWidget, OrganisationTailNumberDependedPickWidget
from handling.models import HandlingRequestMovement, HandlingRequestRecurrence, MovementDirection, HandlingRequest
from handling.utils.client_notifications import handling_request_received_push_notification
from handling.utils.handling_request_create import create_recurrence_handling_request
from handling.utils.localtime import get_utc_from_airport_local_time
from handling.utils.validators import validate_handling_request_for_duplicate_v2
from organisation.form_widgets import OrganisationPickWidget, OrganisationPersonPickWidget
from organisation.models import Organisation
from user.models import Person


class HandlingRequestForm(PopRequestMixin, forms.ModelForm):
    IS_LOCAL_TIME_CHOICES = (
        (False, _("UTC")),
        (True, _("Local"))
    )
    arrival_date = forms.DateTimeField(
        label='Date',
        required=True,
    )
    arrival_time = forms.TimeField(
        label='Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )
    arrival_is_local_timezone = forms.TypedChoiceField(
        label='Timezone',
        required=False,
        initial=False,
        coerce=lambda x: x == 'True',
        choices=IS_LOCAL_TIME_CHOICES,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )
    arrival_airport = forms.ModelChoiceField(
        label='Arrival From Airport',
        required=False,
        widget=HandlingRequestLocationPickWidget(attrs={
            'class': 'form-control'
        }),
        queryset=Organisation.objects.handling_request_locations(),
    )
    arrival_crew = forms.CharField(
        label='Crew',
        widget=widgets.NumberInput(attrs={
            'class': 'form-control',
        })
    )
    arrival_is_passengers_onboard = HandlingRequestMovement.is_passengers_onboard.field.formfield(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'danger',
            }),
    )
    arrival_is_passengers_tbc = HandlingRequestMovement.is_passengers_tbc.field.formfield(
        required=False,
        widget=forms.CheckboxInput(
            attrs={'class': 'form-check-input mt-0'}),
    )
    arrival_passengers = HandlingRequestMovement.passengers.field.formfield(
        widget=forms.NumberInput(
            attrs={'class': 'form-control'}),
    )

    # Departure fields
    departure_date = forms.DateTimeField(
        label='Date',
        required=True,
        widget=DatePickerInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
        }),
    )
    departure_time = forms.TimeField(
        label='Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )
    departure_is_local_timezone = forms.TypedChoiceField(
        label='Timezone',
        required=False,
        initial=False,
        coerce=lambda x: x == 'True',
        choices=IS_LOCAL_TIME_CHOICES,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )
    departure_airport = forms.ModelChoiceField(
        required=False,
        label='Departure To Airport',
        widget=HandlingRequestLocationPickWidget(attrs={
            'class': 'form-control'
        }),
        queryset=Organisation.objects.handling_request_locations(),
    )
    departure_crew = forms.CharField(
        label='Crew',
        widget=widgets.NumberInput(attrs={
            'class': 'form-control',
        })
    )
    departure_is_passengers_onboard = HandlingRequestMovement.is_passengers_onboard.field.formfield(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'danger',
            }),
    )
    departure_is_passengers_tbc = HandlingRequestMovement.is_passengers_tbc.field.formfield(
        required=False,
        widget=forms.CheckboxInput(
            attrs={'class': 'form-check-input mt-0'}),
    )
    departure_passengers = HandlingRequestMovement.passengers.field.formfield(
        widget=forms.NumberInput(
            attrs={'class': 'form-control'}),
    )

    enable_recurrence = forms.BooleanField(
        label='Enable Recurrence',
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'd-block',
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'danger',
            }),
    )

    specific_recurrence_dates = forms.CharField(
        label='Specific Recurrence Dates',
        required=False,
        widget=widgets.DateTimeInput(attrs={
            'id': 'id_specific_recurrence_dates',
            'class': 'form-control',
            'data-hr-recurrence-datepicker': '',
            'placeholder': 'Enter arrival dates',
            'autocomplete': 'off',
        }),
    )

    operating_days = WeekdayFormField(
        label='Operating Day(s) of Week',
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
    )

    final_recurrence_date = forms.CharField(
        label='Final Recurrence Date',
        required=False,
        widget=widgets.DateTimeInput(attrs={
            'id': 'id_final_recurrence_date',
            'class': 'form-control',
            'data-hr-final-recurrence-datepicker': '',
            'autocomplete': 'off',
        }),
    )

    weeks_of_recurrence = HandlingRequestRecurrence.weeks_of_recurrence.field.formfield(
        widget=widgets.TextInput(attrs={
            'class': 'form-control',
        }),
    )

    def clean_specific_recurrence_dates(self):
        input_value = self.cleaned_data['specific_recurrence_dates']
        result = []
        if input_value:
            dates = input_value.split(",")
            for date in dates:
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                result.append(date_obj)
        return result

    def clean_final_recurrence_date(self):
        input_value = self.cleaned_data['final_recurrence_date']
        date_obj = None
        if input_value:
            date_obj = datetime.strptime(input_value, "%Y-%m-%d")
        return date_obj

    def clean(self):
        cleaned_data = super().clean()
        tail_number = cleaned_data.get('tail_number')
        enable_recurrence = cleaned_data.get('enable_recurrence')
        specific_recurrence_dates = cleaned_data.get('specific_recurrence_dates')
        final_recurrence_date = self.cleaned_data.get('final_recurrence_date')

        # Combine date and time into datetime
        arrival_date = cleaned_data['arrival_date']
        arrival_time = cleaned_data['arrival_time']
        self.arrival_datetime = arrival_date.combine(arrival_date, arrival_time)

        # Validate arrival datetime
        arrival_is_local_timezone = self.cleaned_data.get('arrival_is_local_timezone', None)
        arrival_datetime_to_validate = self.arrival_datetime
        if arrival_is_local_timezone:
            arrival_datetime_to_validate = get_utc_from_airport_local_time(self.arrival_datetime,
                                                                           self.cleaned_data['airport'])
        else:
            arrival_datetime_to_validate = arrival_datetime_to_validate.replace(tzinfo=pytz.UTC)

        if arrival_datetime_to_validate < timezone.now() and not self.p_create_retrospective_sfr:
            self.add_error('arrival_date', ValidationError("Can't be in the past"))
            self.add_error('arrival_time', ValidationError("Can't be in the past"))

        departure_date = cleaned_data['departure_date']
        departure_time = cleaned_data['departure_time']
        self.departure_datetime = departure_date.combine(departure_date, departure_time)

        # Validate departure datetime
        departure_is_local_timezone = self.cleaned_data.get('departure_is_local_timezone', None)
        departure_datetime_to_validate = self.departure_datetime
        if departure_is_local_timezone:
            departure_datetime_to_validate = get_utc_from_airport_local_time(self.departure_datetime,
                                                                             self.cleaned_data['airport'])
        else:
            departure_datetime_to_validate = departure_datetime_to_validate.replace(tzinfo=pytz.UTC)

        if departure_datetime_to_validate < timezone.now() and not self.p_create_retrospective_sfr:
            self.add_error('departure_date', ValidationError("Can't be in the past"))
            self.add_error('departure_time', ValidationError("Can't be in the past"))

        # Validate departure over arrival datetime
        if departure_datetime_to_validate < arrival_datetime_to_validate:
            departure_earlier_than_arrival_msg = 'Departure cannot be earlier than Arrival'
            self.add_error('departure_time', ValidationError(departure_earlier_than_arrival_msg))
            self.add_error('departure_date', ValidationError(departure_earlier_than_arrival_msg))

        # Validate recurrence options
        if enable_recurrence:
            if specific_recurrence_dates:
                for date in specific_recurrence_dates:
                    if date < timezone.now().date() or date < arrival_datetime_to_validate.date():
                        self.add_error('specific_recurrence_dates',
                                       ValidationError("Date can't be in the past or earlier than arrival date"))
            if final_recurrence_date:
                if final_recurrence_date.replace(tzinfo=pytz.UTC) < timezone.now() or \
                        final_recurrence_date.replace(tzinfo=pytz.UTC) < arrival_datetime_to_validate:
                    self.add_error('final_recurrence_date',
                                   ValidationError("Date can't be in the past or earlier than arrival date"))

        # Validate for duplicate
        duplicate_request = validate_handling_request_for_duplicate_v2(
            organisation_id=cleaned_data['customer_organisation'].pk,
            callsign=cleaned_data['callsign'],
            arrival_date=arrival_datetime_to_validate,
            departure_date=departure_datetime_to_validate,
            tail_number_id=tail_number.pk if tail_number else None,
            airport_id=cleaned_data['airport'].pk,
            mission_number=cleaned_data['mission_number'],
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

    def clean_fuel_required(self):
        fuel_required = self.cleaned_data['fuel_required']
        if fuel_required == 'NO_FUEL':
            fuel_required = None
        else:
            fuel_required = MovementDirection.objects.get(pk=fuel_required)

        return fuel_required

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def save(self, commit=True):
        handling_request = super().save(commit=False)
        enable_recurrence = self.cleaned_data.get('enable_recurrence')
        specific_recurrence_dates = self.cleaned_data.get('specific_recurrence_dates')
        operating_days = self.cleaned_data.get('operating_days')
        final_recurrence_date = self.cleaned_data.get('final_recurrence_date')
        weeks_of_recurrence = self.cleaned_data.get('weeks_of_recurrence')

        created = True if not handling_request.pk else False
        # Save Handling Request object
        handling_request.created_by = self.request.user.person
        if self.request.app_mode == 'ops_portal':
            handling_request.meta_creation_source = 'Ops Portal'
        elif self.request.app_mode == 'dod_portal':
            handling_request.meta_creation_source = 'Planners Portal'

        if self.original_request:
            handling_request.meta_creation_source += f' (copied from {self.original_request.reference})'

        handling_request.skip_signal = True
        handling_request.save()
        delattr(handling_request, 'skip_signal')

        # Create Arrival movement record
        try:
            arrival_movement = HandlingRequestMovement.objects.get(request=handling_request,
                                                                   direction_id='ARRIVAL')
        except HandlingRequestMovement.DoesNotExist:
            arrival_movement = HandlingRequestMovement(request=handling_request,
                                                       direction_id='ARRIVAL')
        arrival_movement.airport = self.cleaned_data['arrival_airport']
        arrival_movement.date = self.arrival_datetime
        arrival_movement.crew = self.cleaned_data['arrival_crew']
        arrival_movement.is_passengers_onboard = self.cleaned_data['arrival_is_passengers_onboard']
        arrival_movement.is_passengers_tbc = self.cleaned_data['arrival_is_passengers_tbc']
        arrival_movement.passengers = self.cleaned_data['arrival_passengers']
        arrival_movement.is_datetime_local = self.cleaned_data['arrival_is_local_timezone']
        arrival_movement.save()

        # Create departure movement record
        try:
            departure_movement = HandlingRequestMovement.objects.get(request=handling_request,
                                                                     direction_id='DEPARTURE')
        except HandlingRequestMovement.DoesNotExist:
            departure_movement = HandlingRequestMovement(request=handling_request,
                                                         direction_id='DEPARTURE')

        departure_movement.airport = self.cleaned_data['departure_airport']
        departure_movement.date = self.departure_datetime
        departure_movement.crew = self.cleaned_data['departure_crew']
        departure_movement.is_passengers_onboard = self.cleaned_data['departure_is_passengers_onboard']
        departure_movement.is_passengers_tbc = self.cleaned_data['departure_is_passengers_tbc']
        departure_movement.passengers = self.cleaned_data['departure_passengers']
        departure_movement.is_datetime_local = self.cleaned_data['departure_is_local_timezone']
        departure_movement.save()

        self.save_m2m()

        if created:
            handling_request.mission_crew.update(is_primary_contact=True)

        if enable_recurrence:
            days_gap = abs((departure_movement.date - arrival_movement.date).days)
            recurrence_requests = []

            specific_recurrence_dates_list = [date.strftime('%Y-%m-%d') for date in specific_recurrence_dates]
            specific_recurrence_dates_list_str = ','.join(specific_recurrence_dates_list) if \
                specific_recurrence_dates_list else None

            recurrence_obj = HandlingRequestRecurrence.objects.create(
                specific_recurrence_dates=specific_recurrence_dates_list_str,
                operating_days=operating_days,
                final_recurrence_date=final_recurrence_date,
                weeks_of_recurrence=weeks_of_recurrence,
            )

            recurrence_obj.handling_requests.add(handling_request, through_defaults={})

            if specific_recurrence_dates:
                for recurrence_date in specific_recurrence_dates:

                    recurrence_arrival_date = datetime.combine(recurrence_date, self.arrival_datetime.time())
                    recurrence_departure_date = recurrence_arrival_date + timedelta(days=days_gap)
                    recurrence_departure_date = datetime.combine(
                        recurrence_departure_date, self.departure_datetime.time())

                    recurrence_request = create_recurrence_handling_request(
                        original_handling_request=handling_request,
                        arrival_date=recurrence_arrival_date,
                        departure_date=recurrence_departure_date)

                    recurrence_requests.append(recurrence_request)

            elif operating_days:
                if final_recurrence_date:
                    recurrence_dates = [self.arrival_datetime + timedelta(days=x) for x in
                                        range(0, (final_recurrence_date.date()
                                                  - self.arrival_datetime.date()).days + 1)]
                if weeks_of_recurrence:
                    recurrence_dates = [self.arrival_datetime + timedelta(days=x) for x in
                                        range(0, (weeks_of_recurrence * 7) + 1)]

                for recurrence_date in recurrence_dates:
                    if str(recurrence_date.isoweekday()) in operating_days and \
                            recurrence_date > self.departure_datetime:

                        recurrence_arrival_date = datetime.combine(recurrence_date,
                                                                   self.arrival_datetime.time())
                        recurrence_departure_date = recurrence_arrival_date + timedelta(days=days_gap)
                        recurrence_departure_date = datetime.combine(
                            recurrence_departure_date, self.departure_datetime.time())

                        recurrence_request = create_recurrence_handling_request(
                            original_handling_request=handling_request,
                            arrival_date=recurrence_arrival_date,
                            departure_date=recurrence_departure_date)

                        recurrence_requests.append(recurrence_request)

            # Trigger post_save signal to send email notifications
            for recurrence_request in recurrence_requests:
                recurrence_obj.handling_requests.add(recurrence_request, through_defaults={})
                post_save.send(HandlingRequest, instance=recurrence_request, created=created)

        # "Copy S&F Request" functionality functions
        if self.original_request:
            # Copy Mission Crew to new S&F Request
            original_request_crew = self.original_request.mission_crew.exclude(
                is_primary_contact=True).all()
            for crew_position in original_request_crew:
                crew_position.pk = None
                crew_position.handling_request = handling_request
                crew_position.save()

            # Copy Arrival Services
            arrival_services = self.original_request.arrival_movement.hr_services.exclude(
                pk__in=handling_request.arrival_movement.hr_services.values_list('pk'),
            )
            for hr_service in arrival_services:
                hr_service.pk = None
                hr_service.booking_confirmed = None
                hr_service.updated_by = None
                hr_service.movement = handling_request.arrival_movement
                hr_service.save()

            # Copy Departure Services
            departure_services = self.original_request.departure_movement.hr_services.exclude(
                pk__in=handling_request.departure_movement.hr_services.values_list('pk'),
            )
            for hr_service in departure_services:
                hr_service.pk = None
                hr_service.booking_confirmed = None
                hr_service.updated_by = None
                hr_service.movement = handling_request.departure_movement
                hr_service.save()

        # Trigger post_save signal to create/update fuel order
        post_save.send(HandlingRequest, instance=handling_request, created=created)

        # Send Handling Request receive confirmation push
        handling_request_received_push_notification.apply_async(args=(handling_request.id,), countdown=2)

        return handling_request

    def __init__(self, *args, **kwargs):
        self.original_request = kwargs.pop('original_request', None)
        super().__init__(*args, **kwargs)

        self.p_create_retrospective_sfr = self.request.user.has_perm('handling.p_create_retrospective_sfr')

        date_options = FlatpickrOptions(
            altFormat="Y-m-d",
            minDate=timezone.now().strftime('%Y-%m-%d') if not self.p_create_retrospective_sfr else '',
        )
        self.fields['arrival_date'].widget = DatePickerInput(
            attrs={'class': 'form-control'},
            options=date_options,
        )

        self.fields['departure_date'].widget = DatePickerInput(
            attrs={'class': 'form-control'},
            options=date_options,
        )

        # 'fuel_unit' default ordering
        self.fields['fuel_unit'].queryset = self.fields['fuel_unit'].queryset.order_by('id')
        self.fields['airport'].queryset = Organisation.objects.handling_request_locations()

        # S&F Request Editing
        if self.instance.id:
            arrival_movement = self.instance.movement.filter(direction_id='ARRIVAL').first()
            self.fields['arrival_date'].initial = arrival_movement.date
            self.fields['arrival_time'].initial = arrival_movement.date.strftime("%H:%M")
            self.fields['arrival_airport'].initial = arrival_movement.airport
            self.fields['arrival_crew'].initial = arrival_movement.crew
            self.fields['arrival_passengers'].initial = arrival_movement.passengers

            departure_movement = self.instance.movement.filter(direction_id='DEPARTURE').first()
            self.fields['departure_date'].initial = departure_movement.date
            self.fields['departure_time'].initial = departure_movement.date.strftime("%H:%M")
            self.fields['departure_airport'].initial = departure_movement.airport
            self.fields['departure_crew'].initial = departure_movement.crew
            self.fields['departure_passengers'].initial = departure_movement.passengers

        self.fields['fuel_required'].empty_label = 'When fuel required?'
        self.fields['fuel_unit'].empty_label = 'Fuel quantity unit type'
        self.fields['fuel_unit'].initial = 1
        self.fields['tail_number'].empty_label = 'Pick Tail Number or leave empty'
        self.fields['arrival_airport'].empty_label = ''
        self.fields['departure_airport'].empty_label = ''

        # S&F Request Copy
        if self.original_request:
            self.fields['customer_organisation'].initial = self.original_request.customer_organisation
            self.fields['crew'].initial = self.original_request.primary_contact
            self.fields['airport'].initial = self.original_request.airport
            self.fields['aircraft_type'].initial = self.original_request.aircraft_type
            self.fields['fuel_quantity'].initial = self.original_request.fuel_quantity
            self.fields['fuel_required'].initial = self.original_request.fuel_required
            self.fields['fuel_prist_required'].initial = self.original_request.fuel_prist_required

        if self.request.user.is_superuser:
            self.fields['tail_number'].queryset = AircraftHistory.objects.include_test_aircraft().all()

        if self.request.app_mode == 'ops_portal':
            del self.fields['handling_agent']

        # DoD Portal User restrictions
        dod_selected_position = getattr(self.request, 'dod_selected_position', None)
        dod_selected_position_perms = getattr(self.request, 'dod_selected_position_perms', None)
        if dod_selected_position:
            self.fields['handling_agent'].widget = PreferredGroundHandlingPickWidget(
                request=self.request,
            )
            self.fields['customer_organisation'].initial = dod_selected_position.organisation
            self.fields['customer_organisation'].disabled = True
        if dod_selected_position_perms:
            if 'dod_planners' not in dod_selected_position_perms:
                self.fields['crew'].initial = [self.request.user.person]
                self.fields['crew'].disabled = True
                # Restrict Aircraft types only to 'flight_crew' user position types
                self.fields['aircraft_type'].queryset = dod_selected_position.aircraft_types

        if settings.DEBUG:
            self.fields['customer_organisation'].initial = Organisation.objects.get(pk=1)
            self.fields['crew'].initial = [Person.objects.get(pk=3), ]
            self.fields['callsign'].initial = 'ABCDEF'
            self.fields['airport'].initial = Organisation.objects.get(pk=800765)
            self.fields['aircraft_type'].initial = 133
            self.fields['fuel_quantity'].initial = 10
            self.fields['fuel_required'].initial = 'ARRIVAL'
            self.fields['arrival_crew'].initial = 1
            self.fields['departure_crew'].initial = 1
            self.fields['arrival_time'].initial = '01:00'
            self.fields['departure_time'].initial = '01:00'

    class Meta:
        model = HandlingRequest
        fields = ['customer_organisation', 'crew', 'aircraft_type',
                  'tail_number', 'callsign', 'mission_number', 'apacs_number', 'apacs_url',
                  'airport', 'notify_dao', 'type', 'handling_agent',
                  'fuel_required', 'fuel_quantity', 'fuel_unit', 'fuel_prist_required', ]
        labels = {
            'crew': 'Primary Mission Contact',
            'handling_agent': 'Preferred Ground Handler (Optional)',
        }
        widgets = {
            "type": HandlingRequestTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'id': 'handling_request_type',
            }),
            "customer_organisation": OrganisationPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'id': 'client_pick',
            }),
            "crew": OrganisationPersonPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "aircraft_type": OrganisationAircraftTypeDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "callsign": widgets.TextInput(attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();this.value = this.value.replace(/\s/g, "");',
            }),
            "mission_number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "apacs_number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "apacs_url": widgets.URLInput(attrs={
                'class': 'form-control',
            }),
            "tail_number": OrganisationTailNumberDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "airport": HandlingRequestLocationPickWidget(attrs={
                'class': 'form-control'
            }),
            "notify_dao": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block mt-3',
            }),
            "fuel_required": s2forms.Select2Widget(attrs={
                'class': 'form-control',
                'required': '',
                'data-minimum-input-length': '0',
            }),
            "fuel_quantity": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "fuel_prist_required": widgets.CheckboxInput(attrs={
                'data-toggle': 'toggle',
                'data-on': 'Yes',
                'data-off': 'No',
                'data-onstyle': 'success',
                'data-offstyle': 'danger',
            }),
            "fuel_unit": UomPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "handling_agent": PreferredGroundHandlingPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }
