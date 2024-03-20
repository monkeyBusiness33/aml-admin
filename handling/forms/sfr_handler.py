from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from django import forms

from handling.form_widgets import HandlingAgentWithBrandPickCreateWidget
from handling.models import HandlingRequest
from organisation.form_widgets import OrganisationPickWidget
from organisation.models import HandlerDetails, Organisation


class HandlingRequestHandlerDetailsForm(forms.Form):
    """
    This form provide additional details fields for "Handler Quick Create" field
    """
    contact_email = HandlerDetails.contact_email.field.formfield(
        widget=forms.TextInput(
            attrs={
                # This static id used in global.js file as anchor
                'id': 'id_contact_email_quick_create',
                'class': 'form-control',
            }
        ),
    )
    contact_phone = HandlerDetails.contact_phone.field.formfield(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )
    ops_frequency = HandlerDetails.ops_frequency.field.formfield(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )


class HandlingRequestGroundHandlingConfirmationForm(BSModalForm):
    confirm_all_services = forms.BooleanField(
        label='Confirm all Services?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )


class HandlingRequestGroundHandlingCancellationForm(BSModalForm):
    mark_as_sent_manually = forms.BooleanField(
        label='Mark as sent manually?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )


class HandlingRequestUpdateHandlerForm(BSModalModelForm, HandlingRequestHandlerDetailsForm):
    mark_as_sent_manually = forms.BooleanField(
        label='Mark as sent manually?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        handling_agent_qs = Organisation.objects.handling_agent().filter(
            handler_details__airport=self.instance.airport.id)
        self.fields['handling_agent'].widget = HandlingAgentWithBrandPickCreateWidget(
            request=self.request,
            queryset=handling_agent_qs,
            handling_request=self.instance,
            initial=self.instance.handling_agent,
            empty_label='Please select Handling Agent'
        )
        self.fields['handling_agent'].empty_label = 'Please select Handling Agent'

    class Meta:
        model = HandlingRequest
        fields = ['handling_agent', ]
        widgets = {
            "handling_agent": OrganisationPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': '0',
            }),
        }
