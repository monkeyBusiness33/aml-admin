from django import forms
from django.forms import widgets
from django.views.generic.edit import ModelFormMixin
from bootstrap_modal_forms.forms import BSModalModelForm

from handling.form_widgets import SfrOpsChecklistItemCategoryPickWidget
from handling.models import SfrOpsChecklistParameter
from organisation.form_widgets import AirportPickWidget


class SfrOpsChecklistItemForm(ModelFormMixin, BSModalModelForm):
    def __init__(self, *args, **kwargs):
        self.location_specific = bool(kwargs.pop('location_specific', False))
        self.fixed_location = kwargs.pop('fixed_location', None)
        super().__init__(*args, **kwargs)

        if not self.location_specific:
            self.fields['location'].widget = forms.HiddenInput()
        else:
            self.fields['location'].required = True

        if self.fixed_location:
            self.fields['location'].initial = self.fixed_location
            self.fields['location'].disabled = True


    class Meta:
        model = SfrOpsChecklistParameter
        fields = ('location', 'category', 'description', 'url')

        widgets = {
            'location': AirportPickWidget(attrs={
                'class': 'form-control',
                'data-placeholder': 'Checklist Item Description',
            }),
            'category': SfrOpsChecklistItemCategoryPickWidget(attrs={
                'class': 'form-control',
            }),
            'description': widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Checklist Item Description',
            }),
            'url': widgets.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Checklist Item URL',
            }),
        }

    def clean(self):
        data = self.cleaned_data

        if not data['description'] and not data['url']:
            self.add_error('description', 'Please specify a description or a URL')
            self.add_error('url', 'Please specify a description or a URL')
