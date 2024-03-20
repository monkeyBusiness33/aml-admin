import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.views.generic.edit import ModelFormMixin
from bootstrap_modal_forms.forms import BSModalModelForm
from django_select2 import forms as s2forms
from organisation.form_widgets import FuelIndexProviderPickWidget
from pricing.form_widgets import FuelIndexDetailsPickWidget, FuelIndexPickWidget, FuelQuantityPricingUnitPickWidget
from pricing.utils import fuel_index_pricing_check_overlap
from ..form_widgets import SourceDocPickWidget, SupplierPickWidget
from ..models import FuelIndex, FuelIndexDetails, FuelIndexPricing


class FuelIndexForm(ModelFormMixin, BSModalModelForm):
    '''
    Form for Fuel Index management
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = FuelIndex
        fields = ('provider', 'name', 'is_active')

        widgets = {
            "name": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Index name',
            }),
            "provider": FuelIndexProviderPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "is_active": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class FuelIndexDetailsForm(ModelFormMixin, BSModalModelForm):
    '''
    Form for Fuel Index management
    '''
    index_period = forms.ChoiceField(label='Period',
                                     required=True,
                                     choices=[('', ''), ('D', 'Prior Day'), ('W', 'Prior Week'),
                                              ('F', 'Prior Fortnight'), ('M', 'Prior Month')],
                                     initial=None,
                                     widget=s2forms.Select2Widget(attrs={
                                         'class': 'form-control',
                                         'data-placeholder': 'Select Index Period',
                                     }))

    index_price = forms.ChoiceField(label='Price',
                                    required=True,
                                    choices=[('', ''), ('L', 'Low'), ('M', 'Mean'), ('H', 'High')],
                                    initial=None,
                                    widget=s2forms.Select2Widget(attrs={
                                        'class': 'form-control',
                                        'data-placeholder': 'Select Index Price',
                                    }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.use_required_attribute = False

        self.fields["index_price"].initial = self.instance.index_price
        self.fields["index_period"].initial = self.instance.index_period

    class Meta:
        model = FuelIndexDetails
        fields = ('fuel_index', 'index_period', 'index_price')

        widgets = {
            "fuel_index": FuelIndexPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class FuelIndexPricingDetailsForm(ModelFormMixin, BSModalModelForm):
    '''
    Form for Fuel Index Pricing management
    '''
    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop('mode', None)
        self.old_index_pricing = kwargs.pop('old_index_pricing', None)
        self.fuel_index = kwargs.pop('fuel_index')
        super().__init__(*args, **kwargs)

        self.fields['is_primary'].initial = self.old_index_pricing.is_primary \
            if self.old_index_pricing else True

        self.fields['fuel_index_details'].queryset = FuelIndexDetails.objects.filter(fuel_index=self.fuel_index)

        if self.old_index_pricing:
            self.fields['fuel_index_details'].initial = self.old_index_pricing.fuel_index_details
            self.fields['fuel_index_details'].disabled = True

            self.fields['pricing_unit'].initial = self.old_index_pricing.pricing_unit

            self.fields['source_organisation'].initial = self.old_index_pricing.source_organisation
            self.fields['source_organisation'].disabled = True

            self.fields['source_document'].initial = self.old_index_pricing.source_document

    class Meta:
        model = FuelIndexPricing
        fields = ('fuel_index_details', 'pricing_unit', 'price', 'valid_from', 'valid_to', 'valid_ufn',
                  'source_organisation', 'source_document', 'is_primary')

        widgets = {
            'fuel_index_details': FuelIndexDetailsPickWidget(
                attrs={
                'class': 'form-control',
            }),
            "pricing_unit": FuelQuantityPricingUnitPickWidget(attrs={
                'class': 'form-control',
            }),
            "price": widgets.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            "valid_from": widgets.DateInput(
                format="%Y-%m-%d",
                attrs={
                    'class': 'form-control',
                    'data-datepicker': '',
                }
            ),
            "valid_to": widgets.DateInput(
                format="%Y-%m-%d",
                attrs={
                    'class': 'form-control',
                    'data-datepicker': '',
                }
            ),
            "valid_ufn": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "source_organisation": SupplierPickWidget(attrs={
                'class': 'form-control',
            }),
            "source_document": SourceDocPickWidget(attrs={
                'class': 'form-control',
            }),
            "is_primary": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_valid_to(self):
        valid_from = self.cleaned_data['valid_from']
        valid_to = self.cleaned_data['valid_to']
        valid_ufn = self.data.get('valid_ufn', False) == 'on'

        if not valid_ufn and isinstance(valid_to, datetime.date) and valid_to <= valid_from:
            raise ValidationError('Valid To date must be after Valid From date')

        return valid_to

    def clean(self):
        cleaned_data = self.cleaned_data

        if self.mode == 'supersede':
            # Additional validation when superseding
            if cleaned_data['valid_from'] <= self.old_index_pricing.valid_from:
                self.add_error('valid_from', ValidationError(
                    f"The valid from date of new pricing has to be after the valid from date of superseded pricing"
                    f" ({self.old_index_pricing.valid_from})"
                ))

        if not self.errors:
            old_pricing_pk = self.old_index_pricing.pk if self.mode == 'supersede' else None
            overlap_msg = fuel_index_pricing_check_overlap(cleaned_data, self.instance.pk, old_pricing_pk=old_pricing_pk)

            if overlap_msg:
                self.add_error(None, ValidationError(overlap_msg))
