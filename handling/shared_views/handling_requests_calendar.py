from django.db.models import Q, OuterRef, Case, When, CharField, Subquery, F, Count
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from rest_framework.generics import GenericAPIView

from core.utils.datatables_functions import get_colored_circle, get_fontawesome_icon
from handling.models import HandlingRequestMovement
from handling.utils.statuses_generators import get_fuel_booking_status_circle, get_ground_handling_status_circle


class HandlingRequestsListCalendarJsonMixin(View):
    queryset = None

    def get_queryset(self):
        qs = self.queryset

        movement_location_qs = HandlingRequestMovement.objects.filter(
            request_id=OuterRef('pk'),
        ).annotate(
            identifier=Case(
                When(airport__details__type_id=8, then=F('airport__airport_details__icao_code')),
                default=F('airport__details__registered_name'),
                output_field=CharField(),
            )
        ).values('identifier')

        if self.request.app_mode == 'ops_portal':
            qs = qs.annotate(
                unread_notes_count=Count('comments',
                                         filter=Q(comments__read_statuses__person=self.request.user.person)
                                                & Q(comments__read_statuses__is_read=False), distinct=True),
            )

        qs = qs.annotate(
            arrival_location_identifier=Subquery(movement_location_qs.filter(direction_id='ARRIVAL')[:1]),
            departure_location_identifier=Subquery(movement_location_qs.filter(direction_id='DEPARTURE')[:1]),
        ).prefetch_related(
            'tail_number',
            'aircraft_type',
            'airport',
            'airport__details',
            'airport__airport_details',
            'sfr_ops_checklist_items',
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
            only_current_q = Q(status__in=[10, 1, 6, 2, 8, 11, ])

        only_assigned_to_me = self.request.GET.get('only_assigned_to_me')
        only_assigned_to_me_q = Q()
        if only_assigned_to_me == 'true':
            if self.request.user.is_staff:
                only_assigned_to_me_q = Q(assigned_mil_team_member=self.person)
            else:
                only_assigned_to_me_q = Q(crew=self.person)

        qs = self.get_queryset()
        qs = qs.filter(
            only_current_q,
            only_assigned_to_me_q,
            (Q(arrival_date__range=[start_date, end_date]) | Q(departure_date__range=[start_date, end_date]))
        ).exclude(
            status__in=[5, 7, 9, ]
        )

        response_list = []

        for handling_request in qs:
            title = '{outstanding_items_icon}{unread_notes_badge}{callsign} / {icao} <span class="ms-2">{fuel_status}'\
                    ' {handling_status}</span><span class="ms-auto float-end">{assigned_initials}<span>'.format(
                        unread_notes_badge=get_colored_circle(color='red', additional_classes='small me-1') \
                            if getattr(handling_request, 'unread_notes_count', False) else '',
                        callsign=handling_request.callsign,
                        icao=handling_request.airport.tiny_repr,
                        fuel_status=get_fuel_booking_status_circle(handling_request.get_fuel_status()),
                        handling_status=get_ground_handling_status_circle(
                            handling_request.get_ground_handling_status()),
                        assigned_initials=handling_request.assigned_mil_team_member.initials if
                        handling_request.assigned_mil_team_member else '--',
                        outstanding_items_icon=handling_request.ops_checklist_outstanding_items_icon
                            if self.request.app_mode == 'ops_portal' else ''
                        )

            tooltip = '{aircraft_type} // {tail_number} <br> ETA {eta} {arrival_icao} <br>' \
                      'ETD {etd} {departure_icao}{unread_notes_count}'.format(
                        aircraft_type=handling_request.aircraft_type.designator,
                        tail_number=handling_request.tail_number if handling_request.tail_number else '',
                        eta=handling_request.eta_date.strftime("%b-%d %H:%M").upper(),
                        arrival_icao=handling_request.arrival_location_identifier or '',
                        etd=handling_request.etd_date.strftime("%b-%d %H:%M").upper(),
                        departure_icao=handling_request.departure_location_identifier or '',
                        unread_notes_count=f"<br><br><span class='text-warning'>{handling_request.unread_notes_count}"
                                           f" unread note{'s' if handling_request.unread_notes_count > 1 else ''}"
                                           f"</span>" if getattr(handling_request, 'unread_notes_count', False) else ''
                        )

            handling_request_url = ''
            if app_mode == 'ops_portal':
                handling_request_url = reverse_lazy('admin:handling_request', kwargs={'pk': handling_request.pk})
            elif app_mode == 'dod_portal':
                handling_request_url = reverse_lazy('dod:request', kwargs={'pk': handling_request.pk})

            item = {
                'title': title,
                'tooltip': tooltip,
                'start': handling_request.eta_date.isoformat(),
                'end': handling_request.etd_date.isoformat(),
                'className': f'hr_status_{handling_request.status}',
                'url': handling_request_url,
            }
            response_list.append(item)

        return JsonResponse(response_list, safe=False)


class HandlingRequestsListCalendarApiMixin(GenericAPIView):
    def get_queryset(self):
        qs = super().get_queryset()
        request_person = getattr(self.request.user, 'person')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        search_q = Q()
        if start_date and end_date:
            search_q = (Q(eta_date__range=[start_date, end_date]) | Q(etd_date__range=[start_date, end_date]))

        only_assigned_to_me = self.request.GET.get('only_assigned_to_me')
        only_assigned_to_me_q = Q()
        if only_assigned_to_me == 'true':
            if self.request.user.is_staff:
                only_assigned_to_me_q = Q(assigned_mil_team_member=request_person)
            else:
                only_assigned_to_me_q = Q(crew=request_person)

        qs = qs.prefetch_related(
            'airport', 'airport__details',
            'aircraft_type', 'tail_number',
            'tail_number__homebase', 'tail_number__homebase__details',
            'tail_number__operator', 'tail_number__operator__details',
            'movement', 'assigned_mil_team_member',
        ).order_by('-eta_date').all()

        qs = qs.filter(search_q, only_assigned_to_me_q)
        qs = qs.order_by('eta_date')

        return qs
