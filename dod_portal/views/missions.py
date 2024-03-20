import json

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, TemplateView

from core.mixins import CustomAjaxDatatableView
from dod_portal.mixins import DodPermissionsMixin
from mission.models import Mission, MissionLeg
from mission.views_shared.communications import MissionConversationCreateMixin
from mission.views_shared.details_update import MissionCallsignUpdateMixin, MissionNumberUpdateMixin, \
    MissionTailNumberUpdateMixin, MissionAircraftTypeUpdateMixin, MissionApacsNumberUpdateMixin, \
    MissionApacsUrlUpdateMixin, MissionConfirmationMixin, MissionCancellationMixin
from mission.views_shared.mission_amend_timings import MissionAmendTimingsMixin
from mission.views_shared.mission_cargo import MissionCargoUpdateMixin
from mission.views_shared.mission_crew import MissionCrewUpdateMixin
from mission.views_shared.mission_leg_update import MissionLegQuickEditMixin, MissionLegChangeAircraftMixin, \
    MissionLegCancelMixin
from mission.views_shared.mission_passengers import MissionPassengersMixin
from mission.views_shared.missions_calendar import MissionsCalendarJsonMixin, MissionDailyScheduleMixin


class MissionsListAjaxView(DodPermissionsMixin, CustomAjaxDatatableView):
    model = Mission
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["pk", "desc"], ]

    # QuerySet Optimizations
    prefetch_related = {
        'aircraft_type'
    }

    def get_initial_queryset(self, request=None):
        missions = request.dod_selected_position.get_missions_list()
        return missions.include_details()

    def sort_queryset(self, params, qs):
        if len(params['orders']):
            if params['orders'][0].column_link.name == 'pk':
                # Default ordering found, use custom instead
                qs = qs.order_by('status_index', 'start_date_val')
            else:
                # Order by selected column
                qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
        return qs

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                if column_link.name == 'mission_number':
                    return qs.filter(mission_number_concat__icontains=column_link.search_value)
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px', },
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
        {'name': 'status_code', 'placeholder': True, 'title': 'Mission Status', 'searchable': False, 'orderable': False,
         'className': 'mission-status',
         'width': '250px',
         },
    ]

    def customize_row(self, row, obj):
        row['callsign'] = f'<span data-url="{obj.get_absolute_url(app_mode="dod_portal")}">{obj.callsign}</span>'
        row['mission_number'] = obj.mission_number_repr
        aircraft_str = 'Tail TBC'
        if obj.aircraft:
            aircraft_str = obj.aircraft
        row['aircraft'] = f'{aircraft_str} ({obj.aircraft_type or ""})'
        row['start_date_val'] = obj.start_date_val.strftime("%Y-%m-%d %H:%M") if obj.start_date_val else ''
        row['end_date_val'] = obj.end_date_val.strftime("%Y-%m-%d %H:%M") if obj.end_date_val else ''
        row['requesting_person'] = obj.requesting_person.fullname
        row['status_code'] = obj.get_status_badge()


class MissionsListView(DodPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Missions Calendar',
             'button_icon': 'fa-calendar-alt',
             'button_url': reverse('dod:missions_calendar'),
             'button_modal': False,
             'button_perm': True,
             },
            {'button_text': 'Add Mission',
             'button_icon': 'fa-plus',
             'button_url': reverse('dod:missions_create'),
             'button_modal': False,
             'button_perm': True,
             },
        ]

        metacontext = {
            'title': 'Missions',
            'page_id': 'dod_missions_list',
            'page_css_class': ' datatable-clickable',
            'datatable_uri': 'dod:missions_list_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class MissionsCalendarJsonResponse(DodPermissionsMixin, MissionsCalendarJsonMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions_qs = self.person_position.get_missions_list()
        self.queryset = MissionLeg.objects.filter(mission__in=missions_qs)


class MissionsCalendarView(DodPermissionsMixin, TemplateView):
    template_name = 'missions_calendar.html'


class MissionDailyScheduleView(DodPermissionsMixin, MissionDailyScheduleMixin):
    pass


class MissionCreateUpdateView(DodPermissionsMixin, TemplateView):
    template_name = 'mission_create_update.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        mission_id = self.kwargs.get('pk')
        if mission_id:
            user_position = getattr(self.request, 'dod_selected_position')
            missions = user_position.get_missions_list(managed=True)
            mission = missions.filter(pk=mission_id).first()
            if not mission:
                raise Http404
            context['mission'] = mission
        return context


class MissionDetailsView(DodPermissionsMixin, DetailView):
    template_name = 'mission_details/00_mission.html'
    model = Mission
    context_object_name = 'mission'

    def get_queryset(self):
        missions = self.person_position.get_missions_list(managed=True)
        queryset = missions.include_details().select_related(
            'organisation'
        ).prefetch_related(
            'aircraft'
        )
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['managed_missions_list'] = self.person_position.managed_missions_list
        return context


class MissionCallsignUpdateView(DodPermissionsMixin, MissionCallsignUpdateMixin):
    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        return user_position.get_missions_list(managed=True)


class MissionNumberUpdateView(DodPermissionsMixin, MissionNumberUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class TailNumberUpdateView(DodPermissionsMixin, MissionTailNumberUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class MissionAircraftTypeUpdateView(DodPermissionsMixin, MissionAircraftTypeUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class MissionApacsNumberUpdateView(DodPermissionsMixin, MissionApacsNumberUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class MissionApacsUrlUpdateView(DodPermissionsMixin, MissionApacsUrlUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class MissionConfirmationView(DodPermissionsMixin, MissionConfirmationMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionCancellationView(DodPermissionsMixin, MissionCancellationMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionConversationCreateView(DodPermissionsMixin, MissionConversationCreateMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionAmendTimingsView(DodPermissionsMixin, MissionAmendTimingsMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionCrewUpdateView(DodPermissionsMixin, MissionCrewUpdateMixin):
    def get_queryset(self):
        return self.person_position.get_missions_list(managed=True)


class MissionPassengersUpdateView(DodPermissionsMixin, MissionPassengersMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionCargoUpdateView(DodPermissionsMixin, MissionCargoUpdateMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except MissionLeg.DoesNotExist:
            raise Http404


class MissionLegQuickEditView(DodPermissionsMixin, MissionLegQuickEditMixin):
    def get_queryset(self):
        missions_qs = self.person_position.get_missions_list(managed=True)
        return MissionLeg.objects.filter(mission__in=missions_qs)


class MissionLegChangeAircraftView(DodPermissionsMixin, MissionLegChangeAircraftMixin):
    def get_queryset(self):
        missions_qs = self.person_position.get_missions_list(managed=True)
        return MissionLeg.objects.filter(mission__in=missions_qs)


class MissionLegCancelView(DodPermissionsMixin, MissionLegCancelMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions_qs = self.person_position.get_missions_list(managed=True)
        self.mission_leg = get_object_or_404(MissionLeg, pk=self.kwargs['pk'], mission__in=missions_qs)
