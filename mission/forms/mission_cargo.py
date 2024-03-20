from django import forms
from django.forms import widgets, BaseModelFormSet

from mission.models import MissionLegCargoPayload


class MissionLegCargoPayloadForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)
        self.fields['mission_legs'].queryset = self.mission.active_legs

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                if self.fields[field].widget.input_type:
                    self.fields[field].widget.attrs['class'] = 'form-check-input is-invalid'
                else:
                    self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

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
            'mission_legs': widgets.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),
        }
        error_messages = {
            "mission_legs": {"required": ""}}


class MissionLegCargoPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.mission:
            self.queryset = MissionLegCargoPayload.objects.filter(mission_legs__mission=self.mission).distinct()
        else:
            self.queryset = MissionLegCargoPayload.objects.none()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mission'] = self.mission
        return kwargs
