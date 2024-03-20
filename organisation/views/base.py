from bootstrap_modal_forms.generic import BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from organisation.forms import OrganisationTagsForm
from organisation.models import Organisation, OrganisationType
from user.mixins import AdminPermissionsMixin


class OrganisationsDuplicateCheckResponse(AdminPermissionsMixin, View):
    permission_required = []

    def get(self, request, *args, **kwargs):
        if is_ajax(self.request.META):
            search_term = request.GET.get('term', '')
            orgs = Organisation.objects.prefetch_related('details').filter(
                Q(details__registered_name__icontains=search_term) |
                Q(details__trading_name__icontains=search_term)
            ).values(
                'id',
                'details__registered_name',
                'details__trading_name',
                'details__type__name',
                'details__country__code',
            )
            return JsonResponse(list(orgs), safe=False)


class OrganisationTagsView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Organisation
    form_class = OrganisationTagsForm
    success_message = 'Organisation tags updated successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Organisation Tags',
            'icon': 'fa-tags',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        organisation = self.get_object()
        response = super().form_valid(form)
        # Reassign default tags even if it removed by the user
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            from ..utils.tags import update_organisation_default_tags
            update_organisation_default_tags(organisation)

        return response


class OrganisationCreateEditMixin(View):
    organisation_id = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation_id = self.kwargs.get('organisation_id', None)

    def has_permission(self):
        # Allow to create new organisation
        if not self.organisation_id and self.request.user.has_perm('core.p_contacts_create'):
            return True
        # Allow update existing organisation
        if self.organisation_id and self.request.user.has_perm('core.p_contacts_update'):
            return True

    def get_success_url(self, organisation: Organisation):
        """
        Decide the redirection target - during org creation process, we may need
        to redirect to type-specific create pages to collect additional type details.
        """
        outstanding_types = self.request.session.get(f'pending_types-{organisation.pk}', None)

        if outstanding_types:
            next_type_pk = outstanding_types.pop(0)
            self.request.session[f'pending_types-{organisation.pk}'] = outstanding_types
            next_type = OrganisationType.objects.filter(pk=next_type_pk).first()
            next_edit_url = next_type.get_edit_url_for_org(organisation)

            if next_edit_url:
                # Redirect to next type create page
                return next_edit_url
            elif len(outstanding_types):
                # Keep trying if any types left
                return self.get_success_url(organisation)

        # Redirect to details if no types left
        return organisation.get_absolute_url()

