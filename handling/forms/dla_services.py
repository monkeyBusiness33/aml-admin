from bootstrap_modal_forms.forms import BSModalModelForm
from django.db.models import Q
from django.forms import widgets

from organisation.form_widgets import DlaServicePickWidget
from organisation.models import DlaService
from pricing.form_widgets import ChargeServicesPickWidget


class DlaServiceForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        charge_services_qs = self.fields['charge_services'].queryset.filter(
            Q(dla_services=None) | Q(dla_services=self.instance)
        ).order_by('name')
        self.fields['charge_services'].queryset = charge_services_qs

    class Meta:
        model = DlaService
        fields = [
            'name',
            'khi_product_code',
            'is_spf_included',
            'is_always_selected',
            'is_dla_visible_arrival',
            'is_dla_visible_departure',
            'charge_services',
            'spf_represented_by',
        ]
        widgets = {
            'name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'khi_product_code': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'is_spf_included': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_always_selected': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_dla_visible_arrival': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_dla_visible_departure': widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'charge_services': ChargeServicesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
            'spf_represented_by': DlaServicePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }
