from bootstrap_modal_forms.forms import BSModalModelForm
from django.forms import widgets

from core.form_widgets import CountryPickWidget
from organisation.form_widgets import OrganisationWithTypePickWidget, OrganisationPersonPositionPickWidget, \
    EmailFunctionPickWidget, AirportPickWidget, OrganisationEmailControlAddressPickWidget
from organisation.models import OrganisationEmailControlAddress, OrganisationEmailControlRule


class EmailDistributionControlAddressForm(BSModalModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationEmailControlAddress
        fields = [
            'label',
            'email_address',
            'organisation',
            'organisation_person',
        ]

        widgets = {
            'label': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'email_address': widgets.EmailInput(attrs={
                'class': 'form-control exclusive-field exclusive-field-required',
                'data-exclusive-field-group': '1',
            }),
            'organisation': OrganisationWithTypePickWidget(attrs={
                'class': 'form-control exclusive-field exclusive-field-required',
                'data-exclusive-field-group': '1',
            }),
            'organisation_person': OrganisationPersonPositionPickWidget(attrs={
                'class': 'form-control exclusive-field exclusive-field-required',
                'data-exclusive-field-group': '1',
            }),
        }


class EmailDistributionControlRuleForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        self.rule_target = kwargs.pop('rule_target', None)
        super().__init__(*args, **kwargs)

        dynamic_fields = ['recipient_organisation', 'recipient_based_airport', 'recipient_based_country']

        # Keep only single rule target field
        for field_name in dynamic_fields:
            if ((not self.instance.pk and field_name != self.rule_target) or
                    (self.instance.pk and not getattr(self.instance, field_name, None))):
                del self.fields[field_name]
            else:
                self.fields[field_name].required = True

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationEmailControlRule
        fields = [
            'email_function',
            'aml_email',
            'recipient_organisation',
            'recipient_based_airport',
            'recipient_based_country',
            'is_cc',
            'is_bcc',
        ]

        widgets = {
            'email_function': EmailFunctionPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            'aml_email': OrganisationEmailControlAddressPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            'recipient_organisation': OrganisationWithTypePickWidget(attrs={
                'class': 'form-control',
            }),
            'recipient_based_airport': AirportPickWidget(attrs={
                'class': 'form-control',
            }),
            'recipient_based_country': CountryPickWidget(attrs={
                'class': 'form-control',
            }),
            'is_cc': widgets.CheckboxInput(attrs={
                'class': 'form-check-input exclusive-field',
                'data-exclusive-field-group': '1',
            }),
            'is_bcc': widgets.CheckboxInput(attrs={
                'class': 'form-check-input exclusive-field',
                'data-exclusive-field-group': '1',
            }),
        }
