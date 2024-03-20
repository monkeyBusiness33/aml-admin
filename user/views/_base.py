from bootstrap_modal_forms.generic import BSModalUpdateView

from user.forms import PersonTagsForm
from user.mixins import AdminPermissionsMixin
from user.models import Person


class PersonTagsView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Person
    form_class = PersonTagsForm
    success_message = 'Person tags updated successfully'
    permission_required = []

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Person Tags',
            'icon': 'fa-tags',
        }

        context['metacontext'] = metacontext
        return context
