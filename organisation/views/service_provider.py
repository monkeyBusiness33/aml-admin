import json

from ajax_datatable.views import AjaxDatatableView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView

from core.utils.datatables_functions import get_datatable_organisation_status_badge, \
    get_datatable_service_provided_services
from organisation.forms import OrganisationDetailsForm, OrganisationRestictedForm, ServiceProviderLocationFormSet, \
    OrganisationAddressFormSet
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import OrganisationServiceProviderLocation, Organisation, OrganisationDetails, \
    OrganisationRestricted
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class ServiceProvidersListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationServiceProviderLocation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name',
         'foreign_field': 'organisation__details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'organisation__details__trading_name',
         'visible': True},
        {'name': 'delivery_location', 'title': 'Location', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'services_provided', 'title': 'Services Provided', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'is_fbo', 'visible': True, 'choices': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = (f'<span data-url="{obj.organisation.get_absolute_url()}">'
                                  f'{obj.organisation.details.registered_name}</span>')
        if hasattr(obj.delivery_location, 'airport_details'):
            row['delivery_location'] = (f'{obj.delivery_location.details.registered_name} '
                                        f'({obj.delivery_location.airport_details.icao_iata})')
        elif hasattr(obj.delivery_location, 'nasdl_details'):
            row['delivery_location'] = f'{obj.delivery_location.details.registered_name}'
        row['services_provided'] = get_datatable_service_provided_services(obj)
        row['status'] = get_datatable_organisation_status_badge(obj.organisation.operational_status)
        return


class ServiceProvidersListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Service Provider',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:service_provider_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Service Providers',
            'page_id': 'service_providers_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:service_providers_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class ServiceProviderLocationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationServiceProviderLocation
    search_values_separator = '+'
    initial_order = []
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = OrganisationServiceProviderLocation.objects.filter(
            organisation_id=self.kwargs['organisation_id']
        )
        return qs

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'delivery_location', 'title': 'Airport / Location', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'services_provided', 'title': 'Service(s) Provided', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'is_fbo', 'visible': True, 'choices': True, },
    ]

    def customize_row(self, row, obj):
        if hasattr(obj.delivery_location, 'airport_details'):
            row['delivery_location'] = (f'{obj.delivery_location.details.registered_name} '
                                        f'({obj.delivery_location.airport_details.icao_iata})')
        elif hasattr(obj.delivery_location, 'nasdl_details'):
            row['delivery_location'] = f'{obj.delivery_location.details.registered_name}'
        row['services_provided'] = get_datatable_service_provided_services(obj)
        return


class ServiceProviderDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.service_provider()


class ServiceProviderCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'service_provider_edit.html'

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        return self.render_to_response({
            'organisation': organisation,
            'service_provider_locations_formset': ServiceProviderLocationFormSet(
                organisation=organisation,
                prefix='service_provider_locations_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        service_provider_locations_formset = ServiceProviderLocationFormSet(request.POST or None,
                                                                            organisation=organisation,
                                                                            prefix='service_provider_locations_formset_pre')

        # Process only if ALL forms are valid
        if all([
            service_provider_locations_formset.is_valid(),
        ]):
            # Save Service Provider Locations
            instances = service_provider_locations_formset.save(commit=False)
            for instance in instances:
                instance.organisation = organisation
            service_provider_locations_formset.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'service_provider_locations_formset': service_provider_locations_formset,
            })
