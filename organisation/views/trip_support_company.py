import json

from ajax_datatable.views import AjaxDatatableView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView

from core.utils.datatables_functions import get_datatable_organisation_status_badge, \
    get_datatable_trip_support_company_clients
from organisation.forms import OrganisationDetailsForm, OrganisationRestictedForm, TripSupportCompanyClientFormSet, \
    OrganisationAddressFormSet
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OrganisationDetails, OrganisationRestricted
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class TripSupportCompaniesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.trip_support_company()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
            'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'client_operators', 'title': 'Client Operator(s)', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name',
            'visible': True, 'choices': False, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['client_operators'] = get_datatable_trip_support_company_clients(obj)
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class TripSupportCompaniesListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Trip Support Company',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:trip_support_company_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Trip Support Companies',
            'page_id': 'trip_support_companies_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:trip_support_companies_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class TripSupportCompanyDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.trip_support_company()


class TripSupportCompanyClientsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    initial_order = []
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.filter(
                trip_support_companies__organisation_id=self.kwargs['trip_support_company_id'])
        return qs

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Organisation', 'foreign_field': 'details__registered_name',
            'visible': True, 'searchable': False, 'className': 'organisation_reg_name'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'


class TripSupportCompanyCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'trip_support_company_edit.html'

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        return self.render_to_response({
            'organisation': organisation,
            'trip_support_clients_formset': TripSupportCompanyClientFormSet(
                organisation=organisation,
                prefix='trip_support_clients_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        trip_support_clients_formset = TripSupportCompanyClientFormSet(request.POST or None,
                                                                       organisation=organisation,
                                                                       prefix='trip_support_clients_formset_pre')

        # Process only if ALL forms are valid
        if all([
            trip_support_clients_formset.is_valid(),
        ]):
            # Save Trip Support Locations
            instances = trip_support_clients_formset.save(commit=False)
            for instance in instances:
                instance.organisation = organisation
            trip_support_clients_formset.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'trip_support_clients_formset': trip_support_clients_formset,
            })
