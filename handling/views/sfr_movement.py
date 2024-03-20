from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.views.generic.detail import BaseDetailView

from handling.forms.sfr_movement import HandlingRequestUpdateMovementDetailsForm, HandlingRequestUpdatePPRForm
from handling.models import HandlingRequestMovement, HandlingRequest
from user.mixins import AdminPermissionsMixin


class HandlingServiceUpdateMovementDetailsView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_update_movement.html'
    model = HandlingRequestMovement
    form_class = HandlingRequestUpdateMovementDetailsForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        movement = self.get_object()
        handling_request = movement.request

        if movement.direction.code == 'DEPARTURE' and handling_request.is_departure_editing_grace_period:
            text = 'S&F Request is in grace period, movement update will not reset any booking confirmations'
        else:
            text = 'Updating this details services, fuel and parking booking confirmations will be <b>reset</b>.'

        metacontext = {
            'title': f'Update {movement.direction_name} Movement Details',
            'icon': 'fa-sticky-note',
            'text': text,
            'form_id': 'sfr_update_movement',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        form.instance.updated_by = request_person
        return super().form_valid(form)


class HandlingRequestUpdatePPRView(AdminPermissionsMixin, BaseDetailView, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdatePPRForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        handling_request = self.get_object()
        kwargs.update({'handling_request': handling_request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handling_request = self.get_object()

        if handling_request.is_ppr_number_set:
            title = 'Update PPR'
            action_button_text = 'Update'
        else:
            title = 'Confirm PPR'
            action_button_text = 'Confirm'

        metacontext = {
            'title': title,
            'icon': 'fa-clipboard',
            'action_button_class': 'btn-success',
            'action_button_text': action_button_text,
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        handling_request = self.get_object()
        request_person = getattr(self.request.user, 'person')
        response = super().form_valid(form)

        if not is_ajax(self.request.META):
            arrival_ppr_number = form.cleaned_data.get('arrival_ppr_number', None)
            if arrival_ppr_number:
                arrival_movement = handling_request.arrival_movement
                arrival_movement.ppr_number = arrival_ppr_number
                arrival_movement.updated_by = request_person
                arrival_movement.save()

            departure_ppr_number = form.cleaned_data.get('departure_ppr_number', None)
            if departure_ppr_number:
                departure_movement = handling_request.departure_movement
                departure_movement.ppr_number = departure_ppr_number
                departure_movement.updated_by = request_person
                departure_movement.save()

            handling_request.updated_by = request_person
            handling_request.save()

        return response
