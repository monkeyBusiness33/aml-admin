import json

from ajax_datatable.filters import build_column_filter
from django.db.models import Q
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import TemplateView

from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_badge
from handling.models import HandlingRequest
from handling.shared_views.handling_requests_calendar import HandlingRequestsListCalendarJsonMixin
from handling.utils.statuses_generators import get_fuel_booking_status_circle, get_ground_handling_status_circle
from user.mixins import AdminPermissionsMixin


class HandlingRequestsListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = HandlingRequest
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["pk", "desc"], ]
    permission_required = ['handling.p_view']

    # QuerySet Optimizations
    disable_queryset_optimization_only = True
    prefetch_related = {
        'airport',
        'airport__airport_details',
        'airport__details',
        'recurrence_groups_membership',
        'spf',
    }

    def get_initial_queryset(self, request=None):
        qs = HandlingRequest.objects.detailed_list(include_test_requests=self.request.user.is_superuser)
        return qs

    def sort_queryset(self, params, qs):
        if len(params['orders']):
            if params['orders'][0].column_link.name == 'pk':
                # Default ordering found, use custom instead
                qs = qs.order_by('status_index', 'eta_date')
            else:
                # Order by selected column
                qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
        return qs

    default_status_filter = '10,1,6,11,12,2,8,3'

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px', },
        {'name': 'callsign', 'visible': True, 'className': 'url_source_col', 'width': '150px', },
        {'name': 'mission_number', 'visible': True, 'orderable': True, },
        {'name': 'aircraft_type', 'title': 'Aircraft Type',
            'foreign_field': 'aircraft_type__model', 'visible': True, 'width': '300px', },
        {'name': 'eta_date', 'title': 'ETA', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': True, },
        {'name': 'etd_date', 'title': 'ETD', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': True, },
        {'name': 'location', 'title': 'Location', 'searchable': True, 'orderable': False, 'visible': True, },

        {'name': 'crew', 'title': 'Mission Contact', 'visible': True, 'searchable': True},

        {'name': 'mission_type', 'title': 'Mission Type',
            'foreign_field': 'type__name', 'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'assigned_mil_team_member', 'title': 'Assigned To',
         'foreign_field': 'assigned_mil_team_member__details__first_name', 'visible': True, },
        {'name': 'created_at', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'fuel_status', 'title': 'Fuel', 'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'gh_status', 'title': 'GH', 'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'status', 'title': 'Mission Status', 'searchable': True, 'orderable': False,
         'className': 'link multiple-select-filter-col mission-status',
         'initialSearchValue': default_status_filter,
         'width': '250px',
         'choices': (
             (0, 'ALL'),
             (10, 'NEW'),
             (1, 'In Progress'),
             (6, 'Amended'),
             (6, 'Amended Callsign'),
             (2, 'Confirmed'),
             (8, 'Confirmed (tail number TBC)'),
             (12, 'AOG'),
             (3, 'Service unavailable'),
             (4, 'Completed'),
             (7, 'Expired'),
             (5, 'Cancelled'),
         ),
         },
    ]

    def filter_queryset(self, params, qs):
        qs = self.filter_queryset_by_date_range(params.get('date_from', None), params.get('date_to', None), qs)

        if 'search_value' in params:
            qs = self.filter_queryset_all_columns(params['search_value'], qs)

        for column_link in params['column_links']:

            # Default filtering injection
            # if column_link.name == 'status' and column_link.search_value == '':
            #     qs = qs.filter(~Q(status__in=[4, 5, 7]))
            if column_link.name == 'status' and column_link.search_value == '0':
                qs = qs.filter(status__in=[10, 1, 6, 11, 2, 8, 3, 4, 7, 5])

            elif column_link.searchable and column_link.search_value:
                qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        search_filters = Q()

        for column_name in column_names:
            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            if column_name == 'status':
                # Use comma instead of the regular self.search_values_separator
                search_value = [t.strip() for t in search_value.split(',')]
                if '0' in search_value:
                    search_value = ['10', '1', '6', '11', '2', '8', '3', '4', '7', '5']

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)
            elif column_name == 'crew':
                return qs.filter(
                    (Q(mission_crew__person__details__first_name__icontains=search_value) &
                     Q(mission_crew__is_primary_contact=True)) |

                    (Q(mission_crew__person__details__last_name__icontains=search_value) &
                     Q(mission_crew__is_primary_contact=True))
                ).distinct()
            elif column_name == 'location':
                return qs.filter(
                    Q(airport__airport_details__icao_code__icontains=search_value) |
                    Q(airport__airport_details__icao_code__icontains=search_value) |
                    Q(airport__details__registered_name__icontains=search_value)
                ).distinct()
            else:
                # Default behaviour for this function
                if self.search_values_separator and self.search_values_separator in search_value:
                    search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)

    def customize_row(self, row, obj):
        row['callsign'] = f'<span data-target="_blank" data-url="{obj.get_absolute_url()}">{obj.callsign}</span>'
        row['eta_date'] = f'{obj.eta_date.strftime("%Y-%m-%d %H:%M")} UTC' if obj.eta_date else None
        row['etd_date'] = f'{obj.etd_date.strftime("%Y-%m-%d %H:%M")} UTC' if obj.etd_date else None
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")
        row['crew'] = obj.primary_contact_repr
        row['aircraft_type'] = f'{obj.aircraft_type}'
        row['location'] = f'{obj.airport.tiny_repr}'

        if obj.assigned_mil_team_member:
            assigned_mil_team_member = obj.assigned_mil_team_member.fullname
        else:
            assigned_mil_team_member = get_datatable_badge(badge_text='Not yet assigned',
                                                           badge_class='datatable-badge-normal me-1 hr_status_1')
        row['assigned_mil_team_member'] = assigned_mil_team_member

        # Get status of Fuel booking
        row['fuel_status'] = get_fuel_booking_status_circle(obj.fuel_status['code'])
        row['gh_status'] = get_ground_handling_status_circle(obj.ground_handling_status['code'])
        row['status'] = obj.get_status_badge()
        # row['status'] += obj.get_spf_status_badge()
        row['status'] += obj.get_recurrence_group_badge()
        return


class HandlingRequestsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['handling.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'S&F Requests Calendar',
             'button_icon': 'fa-calendar-alt',
             'button_url': reverse('admin:handling_requests_calendar'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('handling.p_view'),
             },

            {'button_text': 'Add Servicing & Fueling Request',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:handling_request_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('handling.p_create'),
             },
        ]

        metacontext = {
            'title': 'Servicing & Fueling Requests',
            'page_id': 'handling_requests_list',
            'page_css_class': ' datatable-clickable',
            'datatable_uri': 'admin:handling_requests_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
            'multiple_select_filters': True,
            'js_scripts': [
                static('assets/js/handling_requests_list_datatable_utils.js')
            ]
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestsListCalendarJsonResponse(AdminPermissionsMixin, HandlingRequestsListCalendarJsonMixin):
    permission_required = ['handling.p_view']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.queryset = HandlingRequest.objects.detailed_list()


class HandlingRequestsListCalendarView(AdminPermissionsMixin, TemplateView):
    template_name = 'handling_requests_calendar.html'
    permission_required = ['handling.p_view']
