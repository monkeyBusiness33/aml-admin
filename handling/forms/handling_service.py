from bootstrap_modal_forms.forms import BSModalModelForm

from core.form_widgets import UomPickWidget, TagPickCreateWidget
from handling.models import HandlingService
from organisation.form_widgets import AirportsPickWidget, OrganisationsPickWidget
from organisation.models import Organisation


class HandlingServiceForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)

        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['name'].widget.attrs['placeholder'] = 'Service visible name'
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        self.fields['always_included'].widget.attrs['class'] = 'form-check-input'
        self.fields['is_spf_visible'].widget.attrs['class'] = 'form-check-input'

        self.fields['is_allowed_free_text'].widget.attrs['class'] = 'form-check-input'
        self.fields['is_allowed_quantity_selection'].widget.attrs['class'] = 'form-check-input'
        self.fields['quantity_selection_uom'].empty_label = 'Start typing unit of measure'

        self.fields['availability'].widget = AirportsPickWidget()
        self.fields['availability'].queryset = Organisation.objects.airport()
        self.fields['availability'].widget.attrs['class'] = 'form-control'
        self.fields['availability'].empty_label = 'Applicable Airports'

        self.fields['organisations'].widget = OrganisationsPickWidget()
        self.fields['organisations'].queryset = Organisation.objects.aircraft_operator_military()
        self.fields['organisations'].widget.attrs['class'] = 'form-control'
        self.fields['organisations'].empty_label = 'Start typing organisation name'

    class Meta:
        model = HandlingService
        fields = [
            'name',
            'is_active',
            'always_included',
            'is_spf_visible',
            'is_allowed_free_text',
            'is_allowed_quantity_selection',
            'quantity_selection_uom',
            'availability',
            'organisations',
        ]

        widgets = {
            "quantity_selection_uom": UomPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class HandlingServiceTagsForm(BSModalModelForm):

    class Meta:
        model = HandlingService
        fields = ['tags', ]
        widgets = {
            "tags": TagPickCreateWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }
