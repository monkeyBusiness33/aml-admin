import json

from ajax_datatable.filters import build_column_filter
from django.db.models import Q, CharField
from django.db.models.functions import Concat
from django.urls import reverse
from django.views.generic import TemplateView

from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_badge
from mission.models import Mission, MissionLeg
from mission.views_shared.missions_calendar import MissionsCalendarJsonMixin
from user.mixins import AdminPermissionsMixin


class MissionsListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = Mission
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["pk", "desc"], ]
    permission_required = ['handling.p_view']

    # QuerySet Optimizations
    prefetch_related = {
        'aircraft_type',
        'assigned_mil_team_member',
    }

    def get_initial_queryset(self, request=None):
        qs = Mission.objects.include_details()
        return qs

    def sort_queryset(self, params, qs):
        if len(params['orders']):
            if params['orders'][0].column_link.name == 'pk':
                # Default ordering found, use custom instead
                qs = qs.order_by('status_index', 'start_date_val')
            else:
                # Order by selected column
                qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
        return qs

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        search_filters = Q()

        for column_name in column_names:
            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            if column_name == 'status_code':
                # Use comma instead of the regular self.search_values_separator
                search_value = [t.strip() for t in search_value.split(',')]
                if '0' in search_value:
                    search_value = ['1', '2', '3', '4', '5', '6', '10']

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)
            if column_name == 'mission_number':
                return qs.filter(mission_number_concat__icontains=search_value)
            else:
                # Default behaviour for this function
                if self.search_values_separator and self.search_values_separator in search_value:
                    search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)

    default_status_filter = '4,3,6,10'

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px', },
        {'name': 'organisation', 'title': 'Unit',
         'foreign_field': 'organisation__details__registered_name', 'visible': True, 'width': '300px', },
        {'name': 'mission_number', 'visible': True, 'orderable': False, },
        {'name': 'callsign', 'visible': True, 'className': 'organisation_reg_name', },
        {'name': 'mission_type', 'title': 'Mission Type',
         'foreign_field': 'type__name', 'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'aircraft', 'title': 'Aircraft',
            'foreign_field': 'aircraft__registration', 'visible': True, },
        {'name': 'start_date_val', 'title': 'Mission Start', 'visible': True, 'orderable': False, },
        {'name': 'end_date_val', 'title': 'Mission End', 'visible': True, 'orderable': False, },
        {'name': 'requesting_person', 'title': 'Mission Contact',
         'foreign_field': 'requesting_person__details__first_name', 'visible': True, },
        {'name': 'status_code', 'placeholder': True, 'title': 'Mission Status', 'searchable': True, 'orderable': False,
         'className': 'link multiple-select-filter-col mission-status',
         'initialSearchValue': default_status_filter,
         'width': '250px',
         'choices': (
             (0, 'ALL'),
             (10, 'New'),
             (4, 'In Progress'),
             (6, 'Amended'),
             (3, 'Confirmed'),
             (2, 'Draft'),
             (5, 'Completed'),
             (1, 'Cancelled'),
         ),
         },
    ]

    def customize_row(self, row, obj):
        row['callsign'] = f'<span data-url="{obj.get_absolute_url()}">{obj.callsign}</span>'
        row['mission_number'] = obj.mission_number_repr
        aircraft_str = 'Tail TBC'
        if obj.aircraft:
            aircraft_str = obj.aircraft
        row['aircraft'] = f'{aircraft_str} ({obj.aircraft_type or ""})'
        row['start_date_val'] = obj.start_date_val.strftime("%Y-%m-%d %H:%M") if obj.start_date_val else ''
        row['end_date_val'] = obj.end_date_val.strftime("%Y-%m-%d %H:%M") if obj.end_date_val else ''
        row['requesting_person'] = obj.requesting_person.fullname

        if obj.assigned_mil_team_member:
            assigned_mil_team_member = obj.assigned_mil_team_member.fullname
        else:
            assigned_mil_team_member = get_datatable_badge(badge_text='Not yet assigned',
                                                           badge_class='datatable-badge-normal me-1 hr_status_1')
        row['assigned_mil_team_member'] = assigned_mil_team_member
        row['status_code'] = obj.get_status_badge()


class MissionsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'missions_list.html'
    permission_required = ['handling.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Missions Calendar',
             'button_icon': 'fa-calendar-alt',
             'button_url': reverse('admin:missions_calendar'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('handling.p_view'),
             },

            {'button_text': 'Add Mission',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:missions_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('handling.p_create'),
             },
        ]

        metacontext = {
            'title': 'Missions List',
            'page_id': 'missions_list',
            'page_css_class': ' datatable-clickable',
            'datatable_uri': 'admin:missions_list_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
            'multiple_select_filters': True,
        }

        context['metacontext'] = metacontext
        return context


class MissionsCalendarJsonResponse(AdminPermissionsMixin, MissionsCalendarJsonMixin):
    permission_required = ['handling.p_view']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.queryset = MissionLeg.objects.all()


class MissionsCalendarView(AdminPermissionsMixin, TemplateView):
    template_name = 'missions_calendar.html'
    permission_required = ['handling.p_view']
