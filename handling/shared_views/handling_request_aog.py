from bootstrap_modal_forms.generic import BSModalFormView, BSModalUpdateView

from core.forms import ConfirmationForm
from handling.forms.sfr_movement import HandlingRequestUpdateMovementDetailsForm
from handling.models import HandlingRequest, HandlingRequestMovement


class HandlingRequestAogMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = ConfirmationForm

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Aircraft On Ground',
            'icon': 'fa-tools',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Submit',
            'cancel_button_class': 'btn-gray-200',
            'alerts': [
                {
                    'text': 'The "AOG" status will be applied to the S&F Request. '
                            'This action will pause processing of the request.',
                    'class': 'alert-danger',
                    'icon': 'exclamation-triangle',
                    'position': 'top',
                }
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.handling_request.updated_by = getattr(self, 'person')
        self.handling_request.is_aog = True
        self.handling_request.save()
        return super().form_valid(form)


class HandlingRequestAircraftServiceableMixin(BSModalUpdateView):
    template_name = 'handling_request/_modal_update_movement.html'
    model = HandlingRequestMovement
    form_class = HandlingRequestUpdateMovementDetailsForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Aircraft Serviceable',
            'icon': 'fa-tools',
            'action_button_class': 'btn-success',
            'action_button_text': 'Submit',
            'cancel_button_class': 'btn-gray-200',
            'alerts': [
                {
                    'text': 'Removing "AOG" status from the S&F Request will un-pause processing of the request. '
                            'Please update departure details of the request',
                    'class': 'alert-success',
                    'icon': 'exclamation-triangle',
                    'position': 'top',
                }
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        form.instance.request.is_aog = False
        form.instance.request.updated_by = form.instance.updated_by
        return super().form_valid(form)
