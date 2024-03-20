from bootstrap_modal_forms.forms import BSModalModelForm
from django.forms import widgets

from handling.models import HandlingRequest


class HandlingRequestParkingConfirmationForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['parking_apron'].widget = widgets.TextInput()
        self.fields['parking_apron'].widget.attrs['class'] = 'form-control'
        self.fields['parking_apron'].widget.attrs['placeholder'] = 'Parking apron'
        self.fields['parking_apron'].required = False

        self.fields['parking_stand'].widget = widgets.TextInput()
        self.fields['parking_stand'].widget.attrs['class'] = 'form-control'
        self.fields['parking_stand'].widget.attrs['placeholder'] = 'Parking Stand'
        self.fields['parking_stand'].required = False

        self.fields['parking_confirmed_on_day_of_arrival'].widget = widgets.CheckboxInput()
        self.fields['parking_confirmed_on_day_of_arrival'].widget.attrs['class'] = 'form-check-input mt-0'

    class Meta:
        model = HandlingRequest
        fields = ('parking_apron', 'parking_stand', 'parking_confirmed_on_day_of_arrival', )
