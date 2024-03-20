import json

from ajax_datatable.views import AjaxDatatableView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView

from core.utils.datatables_functions import get_datatable_organisation_status_badge
from organisation.forms import OrganisationDetailsForm, OrganisationRestictedForm, NasdlDetailsForm, \
    OrganisationAddressFormSet
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OrganisationDetails, OrganisationRestricted, NasdlDetails
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class NasdlListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.nasdl()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Location Name', 'foreign_field': 'details__registered_name',
            'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'type', 'title': 'Type', 'foreign_field': 'nasdl_details__type__description', 'visible': True},
        {'name': 'associated_organisation', 'title': 'Associated Organisation',
            'foreign_field': 'details__department_of__details__registered_name', 'visible': True, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class NasdlListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Non-Airport Location',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:nasdl_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = dict(title='Non-Airport Locations', page_id='nasdl_list',
                           page_css_class='clients_list datatable-clickable', datatable_uri='admin:nasdls_ajax',
                           header_buttons_list=json.dumps(header_buttons_list))

        context['metacontext'] = metacontext
        return context


class NasdlDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.nasdl()


class NasdlCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'nasdl_edit.html'
    permission_required = ['organisation.change_nasdl']

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        nasdl_details = getattr(organisation, 'nasdl_details', NasdlDetails())

        return self.render_to_response({
            'organisation': organisation,
            'nasdl_details_form': NasdlDetailsForm(
                instance=nasdl_details,
                organisation=organisation,
                prefix='nasdl_details_form_pre'),
            })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        nasdl_details = getattr(organisation, 'nasdl_details', NasdlDetails())

        nasdl_details_form = NasdlDetailsForm(request.POST or None,
                                              instance=nasdl_details,
                                              organisation=organisation,
                                              prefix='nasdl_details_form_pre')

        # Process only if ALL forms are valid
        if all([
            nasdl_details_form.is_valid(),
        ]):
            nasdl_details = nasdl_details_form.save(commit=False)
            nasdl_details.organisation = organisation
            nasdl_details.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'nasdl_details_form': nasdl_details_form,
                })
