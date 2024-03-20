from django import forms
from django.forms import widgets, BaseModelFormSet

from core.utils.form_mixins import FormValidationMixin
from mission.models import MissionLegPassengersPayload
from user.form_widgets import PersonGenderPickWidget


class MissionLegPassengersPayloadForm(FormValidationMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)
        self.fields['mission_legs'].queryset = self.mission.active_legs

    class Meta:
        model = MissionLegPassengersPayload
        fields = [
            'identifier',
            'gender',
            'weight',
            'note',
            'mission_legs',
        ]
        widgets = {
            'identifier': widgets.NumberInput(attrs={
                'class': 'form-control d-none passenger-identifier',
            }),
            'gender': PersonGenderPickWidget(attrs={
                'class': 'form-control gender-select',
                'data-minimum-input-length': 0,
            }),
            'weight': widgets.NumberInput(attrs={
                'class': 'form-control passenger-weight-value',
            }),
            'note': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'mission_legs': widgets.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),
        }


class MissionLegPassengersPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.mission:
            self.queryset = MissionLegPassengersPayload.objects.filter(mission_legs__mission=self.mission).distinct()
        else:
            self.queryset = MissionLegPassengersPayload.objects.none()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mission'] = self.mission
        return kwargs
