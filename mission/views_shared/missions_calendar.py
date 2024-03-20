from datetime import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from mission.forms.mission_leg import DailyScheduleForm
from mission.models import Mission, MissionLeg
from mission.utils.mission_leg_html_helpers import mission_leg_get_calendar_event_html


class MissionsCalendarJsonMixin(View):
    queryset = None

    def get_queryset(self):
        qs = self.queryset

        qs = qs.include_mission_and_sfr_status().filter(
            is_cancelled=False,
        ).prefetch_related(
            'mission',
            'mission__assigned_mil_team_member',
            'mission__assigned_mil_team_member__details',
            'turnaround',
            'aircraft_type_override',
            'mission__aircraft_type',

            'aircraft_override',
            'aircraft_override__aircraft__type',
            'mission__aircraft',
            'mission__aircraft__aircraft__type',

            'departure_location__airport_details',
            'arrival_location__airport_details',

            'turnaround__handling_request',
            'turnaround__handling_request',
        )

        return qs

    def get(self, request, *args, **kwargs):
        app_mode = getattr(self.request, 'app_mode')
        start_date = request.GET.get('start')
        start_date = start_date.split('T')[0]

        end_date = request.GET.get('end')
        end_date = end_date.split('T')[0]

        only_current = request.GET.get('only_current')
        only_current_q = Q()
        if only_current == 'true':
            only_current_q = Q(status__in=[10, 1, 6, 2, 8, ])

        qs = self.get_queryset()
        qs = qs.filter(
            # only_current_q,
            arrival_datetime__gte=start_date,
            departure_datetime__lte=end_date,
        ).exclude(
            # status__in=[5, 7, 9, ]
        )

        if app_mode == 'ops_portal':
            qs = qs.filter(~Q(mission_status_code=2))

        qs = qs.distinct()

        response_list = []
        for mission_leg in qs:
            title = ('<div class="mission-calendar-callsign">{callsign}</div>'
                     '<span class="ms-auto float-end">{assigned_initials}</span>'
                     '<span class="ms-auto float-end">{fuel_status} {gh_status}&nbsp</span>'
                     '<br> <div class="text-center">{departure_date} {departure_icao}>'
                     '{arrival_icao} {arrival_date}</div>').format(
                callsign=mission_leg.get_callsign(),
                fuel_status=mission_leg.sfr_fuel_status_badge or '--',
                gh_status=mission_leg.sfr_gh_status_badge or '--',
                assigned_initials=mission_leg.mission.assigned_mil_team_member.initials if
                mission_leg.mission.assigned_mil_team_member else '--',
                departure_date=mission_leg.departure_datetime.strftime("%H:%M"),
                departure_icao=mission_leg.departure_location.tiny_repr,
                arrival_date=mission_leg.arrival_datetime.strftime("%H:%M"),
                arrival_icao=mission_leg.arrival_location.tiny_repr,
            )

            tooltip = ('{aircraft_type} // {tail_number} <br>'
                       'Callsign: {callsign} <br> Mission Number: {mission_number}').format(
                aircraft_type=mission_leg.aircraft_type.designator if mission_leg.aircraft_type else '',
                tail_number=mission_leg.tail_number or 'Not yet assigned',
                mission_number=mission_leg.mission.mission_number_repr,
                callsign=mission_leg.get_callsign(),
            )

            mission_url = ''
            if app_mode == 'ops_portal':
                mission_url = reverse_lazy('admin:missions_details', kwargs={'pk': mission_leg.mission_id})
            elif app_mode == 'dod_portal':
                mission_url = reverse_lazy('dod:missions_details', kwargs={'pk': mission_leg.mission_id})

            item = {
                'title': title,
                'tooltip': tooltip,
                'start': mission_leg.departure_datetime.isoformat(),
                'end': mission_leg.arrival_datetime.isoformat(),
                'backgroundColor': Mission.STATUS_DETAILS[mission_leg.mission_status_code]['background_color'],
                'textColor': Mission.STATUS_DETAILS[mission_leg.mission_status_code]['text_color'],
                'url': mission_url,
            }
            response_list.append(item)

        return JsonResponse(response_list, safe=False)


class MissionDailyScheduleMixin(TemplateView):
    template_name = 'missions_daily_schedule.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        app_mode = getattr(self.request, 'app_mode')
        organisation = self.person.primary_dod_position.organisation
        date_now = timezone.now().date()

        input_date = self.request.GET.get('date', None)
        working_date = datetime.strptime(input_date, "%Y-%m-%d").date() if input_date else date_now

        context['form'] = DailyScheduleForm(date=working_date)

        missions_qs = self.person.primary_dod_position.get_missions_list()
        organisation_fleet = organisation.get_fleet()
        qs = MissionLeg.objects.filter(mission__in=missions_qs)

        qs = qs.include_mission_and_sfr_status().filter(
            is_cancelled=False,
            arrival_datetime__date=working_date,
            departure_datetime__date=working_date,
        )

        # Initialize data structure
        schedule_data = {}
        schedule_data.setdefault(None, {})
        for tail_number in organisation_fleet:
            schedule_data.setdefault(tail_number, {})

        for i in qs:
            tail_number = i.aircraft_override or i.mission.aircraft
            aircraft_owner_name = tail_number.operator.full_repr if \
                tail_number and tail_number.operator != organisation else None

            schedule_data.setdefault(tail_number, {}).update({
                'registration': tail_number.registration if tail_number else None,
                'operator_name': aircraft_owner_name,
            })
            schedule_data.setdefault(tail_number, {}).setdefault('schedule', []).append(
                mission_leg_get_calendar_event_html(i, app_mode))

        context['schedule_data'] = schedule_data
        context['working_date'] = working_date

        metacontext = {
            'title': 'People',
            'page_id': 'people_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:people_ajax',
        }

        context['metacontext'] = metacontext
        return context
