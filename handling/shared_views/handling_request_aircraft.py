from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalCreateView

from aircraft.models import Aircraft
from handling.forms.sfr_aircraft import HandlingRequestAircraftForm
from handling.forms.sfr_update import HandlingRequestUpdateAircraftTypeForm
from handling.models import HandlingRequest


class HandlingRequestAircraftCreateMixin(BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = Aircraft
    form_class = HandlingRequestAircraftForm
    success_message = 'Aircraft created successfully'

    organisation = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'organisation': self.organisation})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Aircraft',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context


class UpdateAircraftTypeMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateAircraftTypeForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update aircraft type for {obj.callsign}',
            'icon': 'fa-fighter-jet',
            'text': f'Submitting this form "Tail Number" value and services booking confirmation will be reset.',
            'form_id': 'update_aircraft_type_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        form.instance.tail_number_id = None
        return super().form_valid(form)
