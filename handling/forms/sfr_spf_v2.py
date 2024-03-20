from bootstrap_modal_forms.mixins import PopRequestMixin
from django import forms
from django.forms import widgets
from django_select2 import forms as s2forms
from tagify.fields import TagField
from tagify.widgets import TagInput

from core.forms import MultiButtonConfirmationForm
from handling.models import HandlingRequest, HandlingRequestDocumentFile
from organisation.form_widgets import OrganisationPeoplePickWidget
from organisation.models import OrganisationPeople


class RequestSignedSpfForm(MultiButtonConfirmationForm):
    send_to_people = forms.ModelMultipleChoiceField(
        label='People to CC',
        required=False,
        queryset=OrganisationPeople.objects.all(),
        help_text='Select people who will receive copy of the handling request',
        widget=OrganisationPeoplePickWidget(attrs={
            'class': 'form-control',
            'data-minimum-input-length': 0,
        }),
    )
    handler_email = TagField(
        label='Handler Email(s)',
        required=False,
        pattern='^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        widget=TagInput(attrs={
            'class': 'form-control',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.handler_email_addresses = kwargs.pop('handler_email_addresses')
        self.handling_request = kwargs.pop('handling_request')
        super().__init__(*args, **kwargs)

        self.fields['send_to_people'].widget.queryset = self.handling_request.handling_agent.organisation_people.all()

        if not self.handler_email_addresses:
            self.fields['handler_email'].required = True
            self.fields['handler_email'].help_text = 'First email address will be stored to the handler profile'


class SignedSpfUploadForm(PopRequestMixin, forms.Form):
    reference = forms.CharField(
        label='Request Reference',
        required=False,
        disabled=True,
        widget=widgets.TextInput(attrs={
                'class': 'form-control',
            }
        ),
    )

    callsign = forms.CharField(
        label='Callsign',
        required=False,
        disabled=True,
        widget=widgets.TextInput(attrs={
            'class': 'form-control',
        }
        ),
    )
    aircraft_type = forms.CharField(
        label='Aircraft Type',
        required=False,
        disabled=True,
        widget=widgets.TextInput(attrs={
            'class': 'form-control',
        }
        ),
    )

    tail_number = HandlingRequest.tail_number.field.formfield(
        required=True,
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
            'required': '',
            'data-minimum-input-length': '0',
        }),
    )

    submitted_by = forms.CharField(
        label='Submitted By',
        required=True,
        widget=widgets.TextInput(attrs={
            'class': 'form-control',
        }),
    )

    spf_file = HandlingRequestDocumentFile._meta.get_field('file').formfield(
        label='Upload SPF Document',
        required=True,
        widget=widgets.FileInput(
            attrs={
                'class': 'form-control',
            }),
    )

    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request')
        super().__init__(*args, **kwargs)

        self.fields['reference'].initial = self.handling_request.reference
        self.fields['callsign'].initial = self.handling_request.callsign
        self.fields['aircraft_type'].initial = self.handling_request.aircraft_type

        organisation = self.handling_request.customer_organisation
        organisation_fleet = organisation.get_operable_fleet()
        self.fields['tail_number'].queryset = organisation_fleet.filter(
            aircraft__type=self.handling_request.aircraft_type)
        self.fields['tail_number'].initial = self.handling_request.tail_number
        self.fields['tail_number'].empty_label = 'Please select Tail Number'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

