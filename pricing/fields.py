from django import forms
from django.core.exceptions import ValidationError

from pricing.form_widgets import TaxCategoriesPickWidget
from pricing.models import TaxCategory


class CustomModelChoiceField(forms.ModelChoiceField):
    '''
    Overrides self.queryset.get with filtering, distinct selection and getting the first result, to allow selection of
    non unique IPAs (one IPA can be at several locations)
    '''
    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            key = self.to_field_name or "pk"
            if isinstance(value, self.queryset.model):
                value = getattr(value, key)
            value = self.queryset.filter(**{key: value}).distinct()[0]
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise forms.ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )
        return value


def validate_inclusive_taxes(data):
    if 'A' in data and len(data) > 1:
        raise ValidationError("If 'All Applicable Taxes' is selected, no other entries should be selected")


class InclusiveTaxesFormField(forms.MultipleChoiceField):
    default_validators = [validate_inclusive_taxes]

    def __init__(self, *args, **kwargs):
        kwargs.update({
            'label': kwargs.get('label') or 'Inclusive Taxes',
            'required': kwargs.get('required') or False,
            'widget': kwargs.get('widget') or kwargs.get('widget') or TaxCategoriesPickWidget(attrs={
                'class': 'form-control',
            }),

        })
        super(InclusiveTaxesFormField, self).__init__(*args, **kwargs)


class IpaOrganisationReconcileField(forms.ChoiceField):

    def validate(self, value):
        """
        Validate that the input is in self.choices, but first update the choices list
        based on widget's choice list, to add newly created entries.
        """
        for choice in self.widget.choices:
            # Skip empty option
            if choice[0] and choice not in self.choices:
                self.choices.append(choice)

        super().validate(value)
