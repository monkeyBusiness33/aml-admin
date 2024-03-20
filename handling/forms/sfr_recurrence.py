import itertools
from datetime import datetime, timedelta

from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.db import transaction
from django.db.models.signals import post_save
from django.forms import widgets

from handling.models import HandlingRequestRecurrence, HandlingRequest
from handling.utils.handling_request_create import create_recurrence_handling_request
from handling.utils.handling_request_func import handling_request_cancel_actions


class HandlingRequestRecurrenceForm(BSModalModelForm):
    arrival_date = forms.DateTimeField(
        label='Arrival Date',
        required=True,
        widget=widgets.DateTimeInput(attrs={
            'id': 'update_recurrence_arrival_datepicker',
            'class': 'form-control',
            'data-movement-datepicker': '',
            'required': 'required',
            'autocomplete': 'off',
        }))
    arrival_time = forms.TimeField(
        label='Arrival Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )

    departure_date = forms.DateTimeField(
        label='Departure Date',
        required=True,
        widget=widgets.DateTimeInput(attrs={
            'id': 'update_recurrence_departure_datepicker',
            'class': 'form-control',
            'data-movement-datepicker': '',
            'required': 'required',
            'autocomplete': 'off',
        }))
    departure_time = forms.TimeField(
        label='Departure Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )

    class Meta:
        model = HandlingRequestRecurrence
        fields = ['specific_recurrence_dates', 'operating_days', 'final_recurrence_date', 'weeks_of_recurrence', ]
        widgets = {
            "specific_recurrence_dates": widgets.DateTimeInput(attrs={
                'id': 'id_specific_recurrence_dates',
                'class': 'form-control',
                'placeholder': 'Enter arrival dates',
                'autocomplete': 'off',
            }),
            "operating_days": forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),
            "final_recurrence_date": widgets.DateTimeInput(attrs={
                'id': 'id_final_recurrence_date',
                'class': 'form-control',
                'data-hr-final-recurrence-datepicker': '',
                'autocomplete': 'off',
            }),
            "weeks_of_recurrence": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arrival_datetime = None
        self.departure_datetime = None

        next_handling_request = self.instance.get_future_handling_requests().first()

        self.fields['arrival_date'].initial = next_handling_request.arrival_movement.date.date()
        self.fields['arrival_time'].initial = next_handling_request.arrival_movement.date.time().strftime("%H:%M")
        self.fields['departure_date'].initial = next_handling_request.departure_movement.date.date()
        self.fields['departure_time'].initial = next_handling_request.departure_movement.date.time().strftime("%H:%M")

        if self.instance.specific_recurrence_dates:
            arrival_date_str = next_handling_request.arrival_movement.date.date().strftime("%Y-%m-%d")
            specific_recurrence_dates_list = self.instance.specific_recurrence_dates.split(',')
            for recurrence_date in specific_recurrence_dates_list:
                if arrival_date_str >= recurrence_date:
                    specific_recurrence_dates_list.remove(recurrence_date)

            updated_specific_recurrence_dates = ','.join(specific_recurrence_dates_list)
            self.fields['specific_recurrence_dates'].initial = updated_specific_recurrence_dates
            self.initial['specific_recurrence_dates'] = updated_specific_recurrence_dates

    def clean(self):
        cleaned_data = super().clean()

        # Combine date and time into single value
        arrival_date = cleaned_data['arrival_date']
        arrival_time = cleaned_data['arrival_time']
        self.arrival_datetime = arrival_date.combine(arrival_date, arrival_time)

        departure_date = cleaned_data['departure_date']
        departure_time = cleaned_data['departure_time']
        self.departure_datetime = departure_date.combine(departure_date, departure_time)

        return cleaned_data

    def save(self, commit=True):
        request_person = getattr(self.request.user, 'person', None)
        recurrence = super().save(commit=False)
        specific_recurrence_dates = self.cleaned_data.get('specific_recurrence_dates')
        operating_days = self.cleaned_data.get('operating_days')
        final_recurrence_date = self.cleaned_data.get('final_recurrence_date')
        weeks_of_recurrence = self.cleaned_data.get('weeks_of_recurrence')

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            with transaction.atomic():
                recurrence.save()

                # Calculate difference between original arrival and departure movements
                days_gap = abs((self.arrival_datetime.date() - self.departure_datetime.date()).days)

                # Initialize recurrence dates list and add first date
                recurrence_dates_list = [{
                    'arrival_datetime': self.arrival_datetime,
                    'departure_datetime': self.departure_datetime,
                }]

                if specific_recurrence_dates:
                    # Append dates list by recurrence
                    dates = specific_recurrence_dates.split(",")
                    for raw_recurrence_date in dates:
                        recurrence_arrival_date = datetime.strptime(raw_recurrence_date, "%Y-%m-%d")
                        recurrence_departure_date = recurrence_arrival_date + timedelta(days=days_gap)
                        recurrence_departure_date = datetime.combine(
                            recurrence_departure_date, self.departure_datetime.time())
                        recurrence_dates_list.append({
                            'arrival_datetime': recurrence_arrival_date,
                            'departure_datetime': recurrence_departure_date,
                        })
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
                            recurrence_dates_list.append({
                                'arrival_datetime': recurrence_arrival_date,
                                'departure_datetime': recurrence_departure_date,
                            })

                future_handling_requests = recurrence.get_future_handling_requests()
                for recurrence_date, handling_request in itertools.zip_longest(
                        recurrence_dates_list, future_handling_requests):

                    # Update existing S&F Requests
                    if recurrence_date and handling_request:

                        arrival_movement = handling_request.arrival_movement
                        arrival_movement.date = recurrence_date['arrival_datetime']
                        arrival_movement.updated_by = request_person
                        arrival_movement.save()

                        departure_movement = handling_request.departure_movement
                        departure_movement.date = recurrence_date['departure_datetime']
                        departure_movement.updated_by = request_person
                        departure_movement.save()

                    # Create missing S&F Requests
                    elif recurrence_date and not handling_request:
                        original_handling_request = future_handling_requests.first()
                        new_handling_request = create_recurrence_handling_request(
                            original_handling_request=original_handling_request,
                            arrival_date=recurrence_date['arrival_datetime'],
                            departure_date=recurrence_date['departure_datetime'])

                        recurrence.handling_requests.add(new_handling_request, through_defaults={})
                        post_save.send(HandlingRequest, instance=new_handling_request, created=True)

                    # Cancel extra S&F Requests
                    elif handling_request and not recurrence_date:
                        handling_request_cancel_actions(handling_request=handling_request, author=request_person)

        return recurrence
