from django import forms
from django.forms import widgets, BaseModelFormSet

from handling.models import HandlingRequestPassengersPayload, HandlingRequestCargoPayload
from user.form_widgets import PersonGenderPickWidget


class HandlingRequestPassengersPayloadForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                if self.fields[field].widget.__class__.__name__ == 'CheckboxInput':
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
                else:
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data['is_arrival'] and not cleaned_data['is_departure']:
            self.add_error('is_arrival', "This field is required")
            self.add_error('is_departure', "This field is required")
        return cleaned_data

    class Meta:
        model = HandlingRequestPassengersPayload
        fields = ['identifier', 'gender', 'weight', 'note', 'is_arrival', 'is_departure', ]
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
            "is_arrival": widgets.CheckboxInput(attrs={
                'class': 'form-check-input is-arrival-checkbox',
            }),
            "is_departure": widgets.CheckboxInput(attrs={
                'class': 'form-check-input is-departure-checkbox',
            }),
        }


class HandlingRequestPassengersPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.handling_request:
            self.queryset = HandlingRequestPassengersPayload.objects.filter(
                handling_request=self.handling_request).all()
        else:
            self.queryset = HandlingRequestPassengersPayload.objects.none()


class HandlingRequestCargoPayloadForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                if self.fields[field].widget.__class__.__name__ == 'CheckboxInput':
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
                else:
                    existing_class = self.fields[field].widget.attrs['class']
                    self.fields[field].widget.attrs['class'] = f'{existing_class} is-invalid'
        return is_valid

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data['is_arrival'] and not cleaned_data['is_departure']:
            self.add_error('is_arrival', "This field is required")
            self.add_error('is_departure', "This field is required")
        return cleaned_data

    class Meta:
        model = HandlingRequestCargoPayload
        fields = ['description',
                  'length', 'width', 'height', 'weight', 'quantity',
                  'is_dg', 'note', 'is_arrival', 'is_departure', ]
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
            "is_arrival": widgets.CheckboxInput(attrs={
                'class': 'form-check-input is-arrival-checkbox',
            }),
            "is_departure": widgets.CheckboxInput(attrs={
                'class': 'form-check-input is-departure-checkbox',
            }),
        }


class HandlingRequestCargoPayloadBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.handling_request = kwargs.pop('handling_request', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.handling_request:
            self.queryset = HandlingRequestCargoPayload.objects.filter(
                handling_request=self.handling_request).all()
        else:
            self.queryset = HandlingRequestCargoPayload.objects.none()
