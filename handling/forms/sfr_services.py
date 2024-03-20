from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django import forms
from django.forms import widgets

from core.forms import MultiButtonConfirmationFormMixin
from handling.form_widgets import HandlingAgentPickCreateWidget, HandlingServicePickCreateWidget, \
    HandlingServicePickWidget
from handling.forms.sfr_handler import HandlingRequestHandlerDetailsForm
from handling.models import HandlingRequestServices, HandlingRequest, HandlingService
from organisation.models import Organisation


class HandlingServiceConfirmationForm(MultiButtonConfirmationFormMixin, BSModalModelForm,
                                      HandlingRequestHandlerDetailsForm):
    handling_agent = forms.ModelChoiceField(
        label='Handling Agent',
        widget=HandlingAgentPickCreateWidget(),
        queryset=Organisation.objects.handling_agent(),
        required=False,
        empty_label='Please select Handling Agent',
        help_text='Handling Agent will be applied for all related services')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        handling_request = getattr(self.instance.movement, 'request')

        handling_agent_qs = Organisation.objects.handling_agent().filter(
            handler_details__airport=handling_request.airport)
        self.fields['handling_agent'].widget = HandlingAgentPickCreateWidget(
            request=self.request,
            queryset=handling_agent_qs,
            handling_request=handling_request,
            empty_label='Please select Handling Agent'
        )
        self.fields['handling_agent'].initial = self.instance.movement.request.handling_agent

        # Disable "Handling Agent" field for NASDL Locations
        if not handling_request.is_ground_handling_confirmation_applicable:
            self.fields['handling_agent'].disabled = True
            self.fields['handling_agent'].help_text = 'Not applicable for NASDL Location'

        # Disable "Handling Agent" field in case if ground handling already confirmed
        if hasattr(self.instance.movement.request, 'auto_spf'):
            self.fields['handling_agent'].disabled = True

        self.fields['note'].widget = widgets.Textarea()
        self.fields['note'].widget.attrs['class'] = 'form-control'
        self.fields['note'].widget.attrs['rows'] = 3
        self.fields['note'].widget.attrs['placeholder'] = 'Client visible note'

        self.fields['note_internal'].widget = widgets.Textarea()
        self.fields['note_internal'].widget.attrs['class'] = 'form-control'
        self.fields['note_internal'].widget.attrs['rows'] = 3
        self.fields['note_internal'].widget.attrs['placeholder'] = 'Internal note'

    class Meta:
        model = HandlingRequestServices
        fields = ('note', 'note_internal', 'handling_agent', )


class HandlingServicesConfirmationForm(MultiButtonConfirmationFormMixin, BSModalModelForm,
                                       HandlingRequestHandlerDetailsForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        handling_request = getattr(self, 'instance')

        handling_agent_qs = Organisation.objects.handling_agent().filter(
            handler_details__airport=handling_request.airport)
        self.fields['handling_agent'].widget = HandlingAgentPickCreateWidget(
            request=self.request,
            queryset=handling_agent_qs,
            handling_request=handling_request,
            empty_label='Please select Handling Agent'
        )
        self.fields['handling_agent'].initial = handling_request.handling_agent

        # Disable "Handling Agent" field for NASDL Locations
        if not handling_request.is_ground_handling_confirmation_applicable:
            self.fields['handling_agent'].disabled = True
            self.fields['handling_agent'].help_text = 'Not applicable for NASDL Location'

    class Meta:
        model = HandlingRequest
        fields = ('handling_agent',)


class HandlingServiceInternalNoteForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.service.is_allowed_free_text:
            self.fields['booking_text'].required = True
        else:
            del self.fields['booking_text']

        if self.instance.service.is_allowed_quantity_selection:
            original_label = self.fields['booking_quantity'].label
            uom_label = self.instance.service.quantity_selection_uom.description_plural
            self.fields['booking_quantity'].label = f'{original_label} ({uom_label})'
            self.fields['booking_quantity'].required = True
        else:
            pass
            del self.fields['booking_quantity']

    class Meta:
        model = HandlingRequestServices
        fields = ['booking_text', 'booking_quantity', 'note', 'note_internal', ]
        labels = {
            "note": 'Edit Ground Handler Service Note',
            "note_internal": 'Edit Internal AML Service Note',
        }
        widgets = {
            "booking_text": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service require additional details'
            }),
            "booking_quantity": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "note": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'This text will be visible in the ground handler email message'
            }),
            "note_internal": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'This text will be used only as internal AML comments'
            }),
        }


class HandlingRequestAddServiceForm(BSModalModelForm):

    def __init__(self, *args, **kwargs):
        self.movement = kwargs.pop('movement', None)
        super().__init__(*args, **kwargs)

        if self.movement.request.customer_organisation.is_military:
            available_services = HandlingService.objects.dod_services(
                movement_direction=self.movement.direction,
                airport=self.movement.request.airport,
                handling_request=self.movement.request,
            ).exclude(
                pk__in=self.movement.hr_services.values('service_id')
            )

            self.fields['service'].widget = HandlingServicePickCreateWidget(
                queryset=available_services,
                is_dla=True,
                is_spf_visible=True,
                handling_request=self.movement.request,
                request=self.request)

            self.fields['service'].queryset = available_services
            self.fields['service'].empty_label = 'Select regular or create custom service'
        else:
            available_services = HandlingService.objects.regular_services(
                movement_direction=self.movement.direction,
                airport=self.movement.request.airport,
                handling_request=self.movement.request,
            ).exclude(
                pk__in=self.movement.hr_services.values('service_id')
            )
            self.fields['service'].widget = HandlingServicePickWidget()
            self.fields['service'].queryset = available_services
            self.fields['service'].empty_label = 'Please select service'

        self.fields['service'].widget.attrs['data-minimum-input-length'] = 0

    class Meta:
        model = HandlingRequestServices
        fields = ['service', 'booking_text', 'booking_quantity', 'note', ]
        widgets = {
            "booking_text": widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service require additional details'
            }),
            "booking_quantity": widgets.NumberInput(attrs={
                'class': 'form-control',
            }),
            "note": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
        }

    def save(self, commit=True):
        service = super().save(commit=False)
        service.movement = self.movement
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            service.save()

        return service
