from bootstrap_modal_forms.mixins import PopRequestMixin
from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.forms import widgets
from django.utils import timezone

from handling.utils.handling_request_func import reinstate_mission


class HandlingRequestReinstateForm(PopRequestMixin, forms.Form):
    arrival_date = forms.DateTimeField(
        label='Arrival Date',
        required=False,
        widget=widgets.DateTimeInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
            'required': 'required',
        }))
    arrival_time = forms.TimeField(
        label='Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )

    departure_date = forms.DateTimeField(
        label='Date',
        required=False,
        widget=widgets.DateTimeInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
            'required': 'required',
        }))
    departure_time = forms.TimeField(
        label='Time',
        widget=widgets.TextInput(attrs={
            'class': 'form-control timepicker',
        })
    )

    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request', None)
        self.arrival_datetime = None
        self.departure_datetime = None
        super().__init__(*args, **kwargs)
        if self.handling_request.id:
            if not self.handling_request.arrival_movement.date <= timezone.now():
                del self.fields['arrival_date']
                del self.fields['arrival_time']
                del self.fields['departure_date']
                del self.fields['departure_time']

    def clean(self):
        cleaned_data = super().clean()

        # Combine date and time into single datetime value
        arrival_date = cleaned_data.get('arrival_date', None)
        arrival_time = cleaned_data.get('arrival_time', None)
        if arrival_date and arrival_time:
            self.arrival_datetime = arrival_date.combine(arrival_date, arrival_time)

        departure_date = cleaned_data.get('departure_date', None)
        departure_time = cleaned_data.get('departure_time', None)
        if departure_date and departure_time:
            self.departure_datetime = departure_date.combine(departure_date, departure_time)

        return cleaned_data

    def save(self, commit=True):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            reinstate_mission(self.handling_request,
                              self.arrival_datetime,
                              self.departure_datetime,
                              self.request.user.person)
