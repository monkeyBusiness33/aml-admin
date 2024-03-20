from aircraft.forms import AircraftForm
from aircraft.models import Aircraft
from user.mixins import AdminPermissionsMixin
from bootstrap_modal_forms.generic import BSModalUpdateView


class AircraftEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Aircraft
    form_class = AircraftForm
    success_message = 'Aircraft updated successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Aircraft Details',
            'icon': 'fa-edit',
        }

        context['metacontext'] = metacontext
        return context
