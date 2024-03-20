from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.forms import widgets


class MissionsExportForm(BSModalForm):
    start_date = forms.DateTimeField(
        label='Start Date',
        required=True,
        widget=widgets.DateTimeInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
            'required': 'required',
            'autocomplete': 'off',
        }))

    end_date = forms.DateTimeField(
        label='End Date',
        required=True,
        widget=widgets.DateTimeInput(attrs={
            'class': 'form-control',
            'data-datepicker': '',
            'required': 'required',
            'autocomplete': 'off',
        }))

    only_upcoming = forms.BooleanField(
        label='Only export data for upcoming servicing & fueling requests?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    class Meta:
        fields = ['start_date', 'end_date', 'only_upcoming', ]
