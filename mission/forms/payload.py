from django import forms
from django.forms import widgets, BaseModelFormSet

from core.utils.form_mixins import FormValidationMixin
from mission.models import MissionLegPassengersPayload, MissionLegCargoPayload
from user.form_widgets import PersonGenderPickWidget


class MissionLegPassengersPayloadForm(FormValidationMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = MissionLegPassengersPayload
        fields = ['identifier', 'gender', 'weight', 'note', ]
        widgets = {
            "identifier": widgets.NumberInput(attrs={
                'class': 'form-control d-none passenger-identifier',
            }),
            "gender": PersonGenderPickWidget(attrs={
                'class': 'form-control gender-select',
                'data-minimum-input-length': 0,
            }),
            "weight": widgets.NumberInput(attrs={
                'class': 'form-control passenger-weight-value',
            }),
            "note": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionLegPassengersPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission_leg = kwargs.pop('mission_leg', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.mission_leg:
            self.queryset = MissionLegPassengersPayload.objects.filter(mission_leg=self.mission_leg).all()
        else:
            self.queryset = MissionLegPassengersPayload.objects.none()


class MissionLegCargoPayloadForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = MissionLegCargoPayload
        fields = ['description',
                  'length', 'width', 'height', 'weight', 'quantity',
                  'is_dg', 'note', ]
        widgets = {
            "description": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "length": widgets.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'L',
            }),
            "width": widgets.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'W',
            }),
            "height": widgets.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'H',
            }),
            "weight": widgets.NumberInput(attrs={
                'class': 'form-control cargo-weight',
            }),
            "quantity": widgets.NumberInput(attrs={
                'class': 'form-control cargo-quantity',
            }),
            "is_dg": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "note": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class MissionLegCargoPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission_leg = kwargs.pop('mission_leg', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.mission_leg:
            self.queryset = MissionLegCargoPayload.objects.filter(mission_leg=self.mission_leg).all()
        else:
            self.queryset = MissionLegCargoPayload.objects.none()
