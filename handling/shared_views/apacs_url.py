from bootstrap_modal_forms.generic import BSModalUpdateView

from handling.forms.sfr_update import HandlingRequestUpdateApacsUrlForm
from handling.models import HandlingRequest


class ApacsUrlUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateApacsUrlForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update APACS URL',
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)
