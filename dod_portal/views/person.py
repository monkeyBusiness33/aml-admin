from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalFormView, BSModalUpdateView
from django.http import Http404

from dod_portal.mixins import DodPermissionsMixin
from organisation.forms import OrganisationPersonForm
from user.models.person import PersonDetails, Person
from user.views.person_documents import PersonTravelDocumentStatusMixin


class OrganisationPersonCreateView(DodPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = PersonDetails
    form_class = OrganisationPersonForm
    success_message = 'Person created successfully'
    permission_required = ['dod_planners']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        organisation = self.request.dod_selected_position.organisation
        kwargs.update({'organisation': organisation})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Add New Person',
            'icon': 'fa-user-plus',
        }

        context['metacontext'] = metacontext
        return context


class PersonTravelDocumentStatusView(DodPermissionsMixin, PersonTravelDocumentStatusMixin):

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        organisation = self.request.dod_selected_position.organisation
        try:
            self.person = Person.objects.get(
                pk=self.kwargs['person_id'],
                organisation_people__organisation=organisation,
            )
        except Person.DoesNotExist:
            raise Http404
