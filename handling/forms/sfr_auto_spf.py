from django import forms
from tagify.fields import TagField
from tagify.widgets import TagInput

from core.forms import MultiButtonConfirmationForm
from organisation.form_widgets import OrganisationPeoplePickWidget
from organisation.models import OrganisationPeople


class HandlingRequestAutoSpfSend(MultiButtonConfirmationForm):
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
            self.fields['handler_email'].widget.attrs['has_no_primary_email'] = 'true'
            self.fields['handler_email'].help_text = 'First email address will be stored to the handler profile'
