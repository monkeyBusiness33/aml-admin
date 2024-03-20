from bootstrap_modal_forms.mixins import PopRequestMixin, CreateUpdateAjaxMixin
from django import forms
from django.forms import widgets
from django_select2 import forms as s2forms

from handling.form_widgets import IpaOrganisationPickCreateWidget
from handling.models import HandlingRequest, MovementDirection, HandlingRequestFuelBooking


class FuelBookingConfirmationForm(PopRequestMixin, CreateUpdateAjaxMixin, forms.ModelForm):
    reference = forms.CharField(
        label='Request Reference',
        required=False,
        disabled=True,
        widget=widgets.TextInput(attrs={
                'class': 'form-control',
            }
        ),
    )

    fuel_required = HandlingRequest.fuel_required.field.formfield(
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
            'required': '',
            'data-minimum-input-length': '0',
        }),
    )

    fuel_quantity = HandlingRequest.fuel_quantity.field.formfield(
        widget=widgets.NumberInput(attrs={
            'class': 'form-control',
        }),
    )

    fuel_unit = HandlingRequest.fuel_unit.field.formfield(
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
            'required': '',
            'data-minimum-input-length': '0',
        }),
    )
    fuel_prist_required = HandlingRequest.fuel_prist_required.field.formfield(
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = getattr(self.request, 'user', None)

        # 'fuel_unit' default ordering
        self.fields['fuel_unit'].queryset = self.fields['fuel_unit'].queryset.order_by('id')

        airport = getattr(self.instance.handling_request, 'airport')
        ipas_qs = self.fields['ipa'].queryset

        self.fields['ipa'].widget = IpaOrganisationPickCreateWidget(
            request=self.request,
            queryset=ipas_qs.filter(ipa_locations=airport),
            handling_request=self.instance.handling_request,
            )
        self.fields['ipa'].error_messages['invalid_choice'] = "This Organisation already exists but can't be selected."

        if user:
            self.fields['dla_contracted_fuel'].widget.attrs['class'] = 'form-check-input'
            self.fields['fuel_required'].choices = HandlingRequest.FUEL_REQUIRED_CHOICES
            self.fields['fuel_required'].initial = getattr(self.instance.handling_request, 'fuel_required', None)
            self.fields['fuel_quantity'].initial = getattr(self.instance.handling_request, 'fuel_quantity', None)
            self.fields['fuel_unit'].initial = getattr(self.instance.handling_request, 'fuel_unit', None)
            self.fields['fuel_prist_required'].initial = getattr(
                self.instance.handling_request, 'fuel_prist_required', None)
        else:
            self.fields['dla_contracted_fuel'].widget.attrs['class'] = 'form-check-input float-end'
            del self.fields['fuel_required']
            del self.fields['fuel_quantity']
            del self.fields['fuel_unit']
            del self.fields['fuel_prist_required']

        self.fields['reference'].initial = self.instance.handling_request.reference

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def clean_fuel_required(self):
        fuel_required = self.cleaned_data['fuel_required']
        if fuel_required:
            if fuel_required == 'NO_FUEL':
                fuel_required = None
            else:
                fuel_required = MovementDirection.objects.get(pk=fuel_required)

        return fuel_required

    class Meta:
        model = HandlingRequestFuelBooking
        fields = [
            'dla_contracted_fuel',
            'reference',
            'fuel_required',
            'fuel_quantity',
            'fuel_unit',
            'fuel_order_number',
            'ipa',
            'processed_by',
            'fuel_release',
            'fuel_prist_required',
        ]
        widgets = {
            "dla_contracted_fuel": widgets.CheckboxInput(attrs={
            }),
            "reference": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "fuel_order_number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "ipa": IpaOrganisationPickCreateWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "processed_by": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "fuel_release": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
        }


class FuelReleaseForm(PopRequestMixin, CreateUpdateAjaxMixin, forms.ModelForm):

    class Meta:
        model = HandlingRequestFuelBooking
        fields = ['processed_by', 'fuel_release', ]
        widgets = {
            "processed_by": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "fuel_release": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
        }
