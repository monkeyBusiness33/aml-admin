from bootstrap_modal_forms.generic import BSModalUpdateView
from django.http import Http404

from organisation.forms import OrganisationLogoMottoModalForm
from organisation.models import OrganisationLogoMotto
from user.mixins import AdminPermissionsMixin


class OrganisationLogoMottoUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'organisation_logo_motto_modal.html'
    model = OrganisationLogoMotto
    form_class = OrganisationLogoMottoModalForm
    slug_field = 'organisation_id'
    slug_url_kwarg = "organisation_id"
    success_message = "Organisation's Logo/Motto updated"
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Http404:
            return OrganisationLogoMotto(organisation_id=self.kwargs['organisation_id'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Upload/Replace Organisation Logo',
            'icon': 'fa-edit',
        }

        context['metacontext'] = metacontext
        return context
