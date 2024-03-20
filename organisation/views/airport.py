from ajax_datatable.views import AjaxDatatableView
from django.views.generic import TemplateView

from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, IpaLocation
from user.mixins import AdminPermissionsMixin
from core.utils.datatables_functions import get_datatable_organisation_status_badge


class AirportsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.airport()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'icao_code', 'title': 'ICAO Code', 'foreign_field': 'airport_details__icao_code', 'visible': True},
        {'name': 'iata_code', 'title': 'IATA Code', 'foreign_field': 'airport_details__iata_code', 'visible': True},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class AirportsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Airports',
            'page_id': 'airports_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:airports_ajax',
        }

        context['metacontext'] = metacontext
        return context


class AirportGroundHandlersListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.filter(
            handler_details__airport_id=self.kwargs['airport_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'brand', 'title': 'Brand', 'foreign_field': 'details__department_of__details__registered_name',
         'visible': True, },
        {'name': 'type', 'title': 'Type', 'foreign_field': 'handler_details__handler_type__name', 'visible': True, },
        {'name': 'handles_military', 'title': 'Handles Military?', 'visible': True,
         'foreign_field': 'handler_details__handles_military', 'choices': True, 'autofilter': True, },
        {'name': 'handles_airlines', 'title': 'Handles Airlines?', 'visible': True,
         'foreign_field': 'handler_details__handles_airlines', 'choices': True, 'autofilter': True, },
        {'name': 'handles_cargo', 'title': 'Handles Cargo?',
         'foreign_field': 'handler_details__handles_cargo', 'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'handles_ba_ga', 'title': 'Handles GA/BA?',
         'foreign_field': 'handler_details__handles_ba_ga', 'visible': True, 'choices': True, 'autofilter': True, },
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = (f'<span data-url="{obj.get_absolute_url()}">'
                                  f'{obj.details.registered_and_trading_name}</span>')
        return


class AirportBasedOrganisationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.airport_based_organisations(
            self.kwargs['airport_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': True, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'brand', 'title': 'Brand', 'foreign_field': 'details__department_of__details__registered_name',
         'visible': True, },
        {'name': 'type', 'title': 'Type', 'foreign_field': 'details__type__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'is_aml_supplier', 'title': 'Existing AML Supplier?',
         'foreign_field': 'organisation_restricted__is_service_supplier', 'visible': True,
         'choices': True, 'autofilter': True, },
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = (f'<span data-url="{obj.get_absolute_url()}">'
                                  f'{obj.details.registered_and_trading_name}</span>')
        return


class AirportIPAListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = IpaLocation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = IpaLocation.objects.filter(
            location_id=self.kwargs['airport_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Name', 'foreign_field': 'organisation__details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'brand', 'title': 'Brand',
         'foreign_field': 'organisation__details__department_of__details__registered_name', 'visible': True, },
        {'name': 'fuel_available', 'title': 'Fuel Available', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
        {'name': 'is_aml_supplier', 'title': 'Existing AML Supplier?',
         'foreign_field': 'organisation__organisation_restricted__is_service_supplier', 'visible': True,
         'choices': True, 'autofilter': True, },
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = (f'<span data-url="{obj.organisation.get_absolute_url()}">'
                                  f'{obj.organisation.details.registered_and_trading_name}</span>')
        row['fuel_available'] = obj.location_fuel_types_badges
        return


class AirportDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.airport()
