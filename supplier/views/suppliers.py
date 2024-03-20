import json

from django.db.models import Q
from django.views.generic import TemplateView
from ajax_datatable.filters import build_column_filter
from ajax_datatable.views import AjaxDatatableView

from core.utils.datatables_functions import get_datatable_badge, get_datatable_organisation_status_badge
from supplier.models import Supplier
from supplier.utils.suppliers import get_supplier_service_choices
from user.mixins import AdminPermissionsMixin


class SuppliersListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Supplier
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['supplier.p_view']

    def __init__(self):
        super().__init__()

        services_col_index = next(i for i,v in enumerate(self.column_defs) if v['name'] == 'services_provided')

        if services_col_index:
            self.column_defs[services_col_index]['choices'] = get_supplier_service_choices()

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        '''
        A custom filter for the 'services_provided' column to allow searching based on
        multiple values with AND instead of OR. Also, it includes the 'Fuel Seller'
        and 'Ground Handling' tags, which are not GroundService objects.
        '''
        search_filters = Q()

        for column_name in column_names:
            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            if column_name == 'services_provided':
                # Use comma instead of the regular self.search_values_separator
                search_value = [t.strip() for t in search_value.split(',')]

                # Chain all the search values
                for value in search_value:
                    if value == 'FS':
                        qs = qs.filter(tags__pk=2)
                    elif value == 'GH':
                        qs = qs.filter(handler_details__isnull=False)
                    else:
                        column_filter = build_column_filter(column_name, column_obj, column_spec, value, global_filtering)
                        qs = qs.filter(column_filter)

                return qs
            else:
                # Default behaviour for this function
                if self.search_values_separator and self.search_values_separator in search_value:
                    search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name',
         'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name',
         'visible': True},
        {'name': 'services_provided', 'title': 'Services Provided', 'visible': True,
         'm2m_foreign_field': 'service_provider_locations__ground_services', 'lookup_field': '__pk',
         'placeholder': True, 'searchable': True, 'orderable': False,
         'className': 'multiple-select-filter-col', 'width': '500px'},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'

        # Get a string of badges for the following cases:
        # - org is a Fuel Seller (has tag with id = 2)
        # - org has `organisation_handler_details`
        # - one badge per each provided service name (across all locations)
        service_provider_badges = []

        # 'Fuel Seller' badge
        if 2 in obj.tags.values_list('pk', flat=True):
            badge = get_datatable_badge(badge_text='Fuel Seller', badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                                        tooltip_text='Fuel Seller')
            service_provider_badges.append(badge)

        # 'Ground Handling' badge
        if hasattr(obj, 'handler_details'):
            badge = get_datatable_badge(badge_text='Ground Handling', badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                                        tooltip_text='Ground Handling')
            service_provider_badges.append(badge)

        # Service names
        services_list = set()

        for location in obj.service_provider_locations.all():
            services_list.update(location.ground_services.values_list('name', flat=True))

        for service in sorted(services_list):
            badge = get_datatable_badge(badge_text=service, badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                                        tooltip_text=service)
            service_provider_badges.append(badge)

        row['services_provided'] = ''.join(map(str, service_provider_badges))
        row['status'] = get_datatable_organisation_status_badge(obj.details.operational_status)


class SuppliersListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['supplier.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        header_buttons_list = []

        metacontext = {
            'title': 'Suppliers',
            'page_id': 'suppliers_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:suppliers_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
            'multiple_select_filters': True,
        }

        context['metacontext'] = metacontext
        return context
