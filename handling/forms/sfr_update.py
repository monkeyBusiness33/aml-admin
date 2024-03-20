from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from aircraft.forms import AircraftTypePickWidget
from core.form_widgets import AirCardPrefixPickWidget
from core.models import AirCardPrefix
from core.utils.validators import aircard_expiration_validation
from handling.form_widgets import HandlingAgentPickCreateWidget, HandlingRequestTypePickWidget, \
    OrganisationTailNumberDependedPickWidget
from handling.forms.sfr_handler import HandlingRequestHandlerDetailsForm
from handling.models import HandlingRequest
from handling.utils.validators import validate_handling_request_for_duplicate_v2
from organisation.form_widgets import OrganisationPickWidget
from organisation.models import Organisation
from user.form_widgets import PersonPickWidget


class HandlingRequestUnableToSupportForm(BSModalModelForm, HandlingRequestHandlerDetailsForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        handling_agent_qs = Organisation.objects.handling_agent().filter(
            handler_details__airport=self.instance.airport.id)
        self.fields['handling_agent'].widget = HandlingAgentPickCreateWidget(
            request=self.request,
            queryset=handling_agent_qs,
            handling_request=self.instance,
            initial=self.instance.handling_agent,
            empty_label='Please select Handling Agent'
        )
        self.fields['handling_agent'].empty_label = 'Please select Handling Agent'

    class Meta:
        model = HandlingRequest
        labels = {
            'handling_agent': _("Share Ground Handler Contact Details")
        }
        fields = ['decline_reason', 'handling_agent', ]
        widgets = {
            "decline_reason": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            "handling_agent": OrganisationPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }


class HandlingRequestUpdateApacsNumberForm(BSModalModelForm):

    class Meta:
        model = HandlingRequest
        fields = ['apacs_number', ]
        widgets = {
            "apacs_number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class HandlingRequestUpdateApacsUrlForm(BSModalModelForm):

    class Meta:
        model = HandlingRequest
        fields = ['apacs_url', ]
        widgets = {
            "apacs_url": widgets.URLInput(attrs={
                'class': 'form-control',
            }),
        }


class HandlingRequestAssignedTeamMemberUpdateForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not getattr(self.instance, 'assigned_mil_team_member', None):
            self.initial['assigned_mil_team_member'] = self.request.user.person

    class Meta:
        model = HandlingRequest
        fields = ['assigned_mil_team_member', ]
        widgets = {
            "assigned_mil_team_member": PersonPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }


class HandlingRequestMissionNumberUpdateForm(BSModalModelForm):

    class Meta:
        model = HandlingRequest
        fields = ['mission_number', ]
        widgets = {
            "mission_number": forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class HandlingRequestCallsignUpdateForm(BSModalModelForm):

    class Meta:
        model = HandlingRequest
        fields = ['callsign', ]
        widgets = {
            "callsign": forms.TextInput(attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();this.value = this.value.replace(/\s/g, "");',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        handling_request = self.instance
        tail_number = getattr(handling_request, 'tail_number', None)

        # Validate for duplicate
        duplicate_request = validate_handling_request_for_duplicate_v2(
            organisation_id=handling_request.customer_organisation.pk,
            callsign=cleaned_data['callsign'],
            arrival_date=handling_request.arrival_movement.date,
            departure_date=handling_request.departure_movement.date,
            tail_number_id=tail_number.pk if tail_number else None,
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
                field='callsign',
                error=ValidationError(
                    'This Servicing & Fueling Request conflicts with an existing request - '
                    '<a href="{url}">{callsign}</a>'.format(
                        url=duplicate_request_url,
                        callsign=duplicate_request.callsign,
                    )))

        return cleaned_data


class HandlingRequestTypeUpdateForm(BSModalModelForm):

    class Meta:
        model = HandlingRequest
        fields = ['type', ]
        widgets = {
            "type": HandlingRequestTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'id': 'update_handling_request_type',
            }),
        }


class HandlingRequestAirCardDetailsForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use current active prefix if it not yet set
        if not getattr(self.instance, 'air_card_prefix', None):
            self.initial['air_card_prefix'] = AirCardPrefix.objects.active().first()

    class Meta:
        model = HandlingRequest
        fields = ['air_card_prefix', 'air_card_number', 'air_card_expiration', ]
        widgets = {
            "air_card_prefix": AirCardPrefixPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            "air_card_number": widgets.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 8,
                'onkeyup': "this.value=this.value.replace(/[^\d]/,'')"
            }),
            "air_card_expiration": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MM/YY',
            }),
        }

    def clean_air_card_expiration(self):
        air_card_expiration = self.cleaned_data.get('air_card_expiration', None)
        if air_card_expiration:
            validation_result = aircard_expiration_validation(air_card_expiration=air_card_expiration)
            if not validation_result:
                raise ValidationError('AIR Card expired')

        return air_card_expiration


class HandlingRequestUpdateTailNumberForm(BSModalModelForm):
    unassign_tail = forms.BooleanField(
        label='Not yet assigned',
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organisation = self.instance.customer_organisation
        organisation_fleet = organisation.get_operable_fleet()
        self.fields['tail_number'].queryset = organisation_fleet.filter(aircraft__type=self.instance.aircraft_type)
        self.fields['tail_number'].empty_label = 'Please select Tail Number'

    class Meta:
        model = HandlingRequest
        fields = ['unassign_tail', 'tail_number', ]

        widgets = {
            "tail_number": OrganisationTailNumberDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class HandlingRequestUpdateAircraftTypeForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organisation = self.instance.customer_organisation
        self.fields['aircraft_type'].queryset = organisation.aircraft_types

    class Meta:
        model = HandlingRequest
        fields = ['aircraft_type', ]

        widgets = {
            "aircraft_type": AircraftTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }
