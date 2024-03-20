from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets

from aircraft.forms import AircraftTypePickWidget
from core.form_widgets import AirCardPrefixPickWidget
from core.models import AirCardPrefix
from core.utils.validators import aircard_expiration_validation
from handling.form_widgets import HandlingRequestTypePickWidget
from mission.forms._form_widgets import MissionTailNumberDependedPickWidget
from mission.models import Mission
from user.form_widgets import PersonPickWidget


class MissionCallsignForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = ['callsign', ]
        widgets = {
            "callsign": forms.TextInput(attrs={
                'class': 'form-control',
                'onkeyup': 'this.value = this.value.toUpperCase();this.value = this.value.replace(/\s/g, "");',
            }),
        }


class MissionNumberForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = [
            'mission_number_prefix',
            'mission_number',
        ]
        widgets = {
            "mission_number_prefix": forms.TextInput(attrs={
                'class': 'form-control',
            }),
            "mission_number": forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionAssignedTeamMemberUpdateForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = ['assigned_mil_team_member', ]
        widgets = {
            "assigned_mil_team_member": PersonPickWidget(attrs={
                'class': 'form-control',
            }),
        }


class MissionTailNumberForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aircraft'].queryset = self.instance.organisation.get_operable_fleet().filter(
            aircraft__type=self.instance.aircraft_type,
        )

    class Meta:
        model = Mission
        fields = ['aircraft', ]
        labels = {
            'aircraft': 'Tail Number',
        }
        widgets = {
            "aircraft": MissionTailNumberDependedPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class MissionTypeForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = ['type', ]
        widgets = {
            "type": HandlingRequestTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
                'id': 'update_handling_request_type',
            }),
        }


class MissionAircraftTypeForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aircraft_type'].queryset = self.instance.organisation.aircraft_types

    class Meta:
        model = Mission
        fields = ['aircraft_type', ]

        widgets = {
            "aircraft_type": AircraftTypePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }


class MissionApacsNumberForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = ['apacs_number', ]
        widgets = {
            "apacs_number": forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionApacsUrlForm(BSModalModelForm):
    class Meta:
        model = Mission
        fields = ['apacs_url', ]
        widgets = {
            "apacs_url": forms.URLInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionAirCardDetailsForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use current active prefix if it not yet set
        if not getattr(self.instance, 'air_card_prefix', None):
            self.initial['air_card_prefix'] = AirCardPrefix.objects.active().first()

    class Meta:
        model = Mission
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
                'id': 'id_air_card_expiration',
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
