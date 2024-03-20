from ajax_datatable.filters import build_column_filter
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.utils import timezone
from django.views import View
from django.http import HttpResponse

from bootstrap_modal_forms.mixins import PassRequestMixin
from bootstrap_modal_forms.mixins import is_ajax
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalFormView, BSModalUpdateView
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import TemplateView

from core.mixins import CustomAjaxDatatableView
from dod_portal.forms import HandlingServiceInternalNoteForm
from handling.forms.sfr_create import HandlingRequestForm
from handling.forms.sfr_crew import HandlingRequestCrewFormSet
from handling.forms.sfr_movement import HandlingRequestUpdateMovementDetailsForm
from handling.forms.sfr_reinstate import HandlingRequestReinstateForm
from handling.forms.sfr_services import HandlingRequestAddServiceForm
from handling.forms.sfr_update import HandlingRequestUpdateApacsNumberForm, HandlingRequestUpdateTailNumberForm, \
    HandlingRequestCallsignUpdateForm, HandlingRequestMissionNumberUpdateForm
from handling.models import HandlingRequest, HandlingRequestCrew, HandlingRequestServices, HandlingRequestMovement, \
    HandlingRequestRecurrence

from handling.shared_views.apacs_url import ApacsUrlUpdateMixin
from handling.shared_views.communications import HandlingRequestConversationCreateMixin
from handling.shared_views.handling_request_aircraft import UpdateAircraftTypeMixin, HandlingRequestAircraftCreateMixin
from handling.shared_views.handling_request_aog import HandlingRequestAogMixin, HandlingRequestAircraftServiceableMixin
from handling.shared_views.handling_request_cancellation import HandlingRequestCancelMixin
from handling.shared_views.handling_requests_calendar import HandlingRequestsListCalendarJsonMixin
from handling.shared_views.handling_services import HandlingServiceSelect2Mixin
from handling.shared_views.payload import HandlingRequestPayloadMixin
from handling.shared_views.recurrence import UpdateRecurrenceMixin, CancelRecurrenceMixin
from handling.utils.handling_request_pdf import generate_handling_request_pdf
from ..mixins import DodPermissionsMixin, GetHandlingRequestMixin
import json


class HandlingRequestsListAjaxView(DodPermissionsMixin, CustomAjaxDatatableView):
    model = HandlingRequest
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["pk", "desc"], ]

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
        position = request.dod_selected_position
        missions = position.get_sfr_list()

        return missions.detailed_list()

    def sort_queryset(self, params, qs):
        if len(params['orders']):
            if params['orders'][0].column_link.name == 'pk':
                # Default ordering found, use custom instead
                qs = qs.order_by('status_index', 'eta_date')
            else:
                # Order by selected column
                qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'callsign', 'visible': True, 'className': 'sfr_url', },
        {'name': 'mission_number', 'visible': True, },
        {'name': 'aircraft_type', 'title': 'Aircraft Type',
         'foreign_field': 'aircraft_type__model', 'visible': True, },
        {'name': 'eta_date', 'title': 'ETA', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': True, },
        {'name': 'etd_date', 'title': 'ETD', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': True, },
        {'name': 'location', 'title': 'Location', 'searchable': True, 'orderable': False, 'visible': True, },
        {'name': 'crew', 'title': 'Mission Contact', 'visible': True, 'searchable': True},
        {'name': 'mission_type', 'title': 'Mission Type',
         'foreign_field': 'type__name', 'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        search_filters = Q()

        for column_name in column_names:
            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            if column_name == 'status':
                # Use comma instead of the regular self.search_values_separator
                search_value = [t.strip() for t in search_value.split(',')]

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
        request_url = reverse_lazy("dod:request", kwargs={"pk": obj.pk})
        row['callsign'] = f'<span data-url="{request_url}">{obj.callsign}</span>'
        row['eta_date'] = f'{obj.eta_date.strftime("%Y-%m-%d %H:%M")} UTC' if obj.eta_date else None
        row['etd_date'] = f'{obj.etd_date.strftime("%Y-%m-%d %H:%M")} UTC' if obj.etd_date else None
        row['crew'] = obj.primary_contact_repr
        row['aircraft_type'] = f'{obj.aircraft_type}'
        row['location'] = f'{obj.airport.tiny_repr}'
        row['status'] = obj.get_status_badge()
        row['status'] += obj.get_spf_status_badge()
        row['status'] += obj.get_recurrence_group_badge()
        return


class HandlingRequestsListView(DodPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'S&F Requests Calendar',
             'button_icon': 'fa-calendar-alt',
             'button_url': reverse('dod:handling_requests_calendar'),
             'button_modal': False,
             'button_perm': True,
             },
            {'button_text': 'Add Servicing & Fueling Request',
             'button_icon': 'fa-plus',
             'button_url': reverse('dod:request_create'),
             'button_modal': False,
             'button_perm': True,
             },
        ]

        metacontext = {
            'title': 'Servicing & Fueling Requests',
            'page_id': 'dod_requests_list',
            'page_css_class': ' datatable-clickable',
            'datatable_uri': 'dod:requests_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestsListCalendarJsonResponse(DodPermissionsMixin, HandlingRequestsListCalendarJsonMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        user_position = getattr(self.request, 'dod_selected_position')
        self.queryset = user_position.get_sfr_list().detailed_list()


class HandlingRequestsListCalendarView(DodPermissionsMixin, TemplateView):
    template_name = 'handling_requests_calendar.html'


class HandlingRequestsDetailsView(DodPermissionsMixin, DetailView):
    template_name = 'handling_request/00_handling_request.html'
    model = HandlingRequest
    context_object_name = 'handling_request'

    def get_queryset(self):
        missions = self.person_position.get_sfr_list()

        qs = missions.detailed_list().select_related(
            'customer_organisation',
            'customer_organisation__details',
            'handling_agent',
            'handling_agent__details',
            'airport',
            'airport__airport_details',
            'auto_spf',
            'fuel_booking__ipa__details',
        ).prefetch_related(
            'movement',
            'movement__airport__details',
            'movement__airport__airport_details',
            'movement__direction',
            'movement__hr_services',
            'movement__hr_services__service',
            'documents',
            'chat_conversations',
            Prefetch(
                'mission_crew',
                queryset=HandlingRequestCrew.objects.select_related('person', 'person__details'),
            )
        )
        return qs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['managed_sfr_list'] = self.person_position.managed_sfr_list
        return context


class HandlingRequestManageCrewView(DodPermissionsMixin, GetHandlingRequestMixin, BSModalFormView):
    template_name = 'handling_request/_modal_assigned_crew.html'
    form_class = HandlingRequestCrewFormSet
    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handling_request': self.handling_request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Manage Assigned Crew',
            'icon': 'fa-users',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.save()
            self.handling_request.updated_by = getattr(self, 'person')
            self.handling_request.activity_log.create(
                record_slug='sfr_mission_crew_update',
                author=getattr(self, 'person'),
                details=f'Mission Crew has been updated',
            )
            self.handling_request.save()
        return super().form_valid(form)


class HandlingRequestUpdateApacsNumberView(DodPermissionsMixin, GetHandlingRequestMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateApacsNumberForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Diplomatic Clearance',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestUpdateApacsUrlView(DodPermissionsMixin, GetHandlingRequestMixin, ApacsUrlUpdateMixin):
    pass


class HandlingRequestAddServiceView(DodPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestServices
    form_class = HandlingRequestAddServiceForm

    movement = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.movement = get_object_or_404(HandlingRequestMovement, pk=self.kwargs['pk'],
                                          request__customer_organisation=self.person_position.organisation)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'movement': self.movement})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Add Service to Servicing & Fueling Request',
            'icon': 'fa-plus',
            'text': f'You can add Custom DLA service or pick existing ground service',
            'form_id': 'add_services_to_handling_request',
            'action_button_class': 'btn-success',
            'action_button_text': 'Add',
            'cancel_button_class': 'btn-gray-200',
            'js_scripts': [
                static('js/sfr_add_service_modal.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        form.instance.updated_by = request_person
        return super().form_valid(form)


class HandlingRequestCreateView(DodPermissionsMixin, PassRequestMixin, CreateView):
    template_name = 'handling_request_create.html'
    model = HandlingRequest
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'

    def get_success_url(self):
        return reverse('dod:request', kwargs={'pk': self.object.pk})


class HandlingRequestCopyView(DodPermissionsMixin, PassRequestMixin, SuccessMessageMixin, CreateView):
    template_name = 'handling_request_create.html'
    model = HandlingRequest
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'
    success_message = 'Servicing & Fueling Request successfully created'

    original_request = None

    def get_success_url(self):
        return reverse('dod:request', kwargs={'pk': self.object.pk})

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        handling_request_id = self.kwargs.get('handling_request_id')
        if handling_request_id:
            # Return S&F Request only from those that user have access
            user_position = getattr(self.request, 'dod_selected_position')
            position_missions = user_position.get_sfr_list()
            self.original_request = position_missions.filter(pk=handling_request_id).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({'original_request': self.original_request})

        return kwargs


class HandlingRequestUpdateView(DodPermissionsMixin, PassRequestMixin, UpdateView):
    template_name = 'handling_request_create.html'
    model = HandlingRequest
    form_class = HandlingRequestForm
    context_object_name = 'handling_request'

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        return user_position.managed_sfr_list

    def get_success_url(self):
        return reverse('dod:request_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        arrival_movement = obj.movement.filter(direction_id='ARRIVAL').first()
        departure_movement = obj.movement.filter(
            direction_id='DEPARTURE').first()

        context['arrival_movement'] = arrival_movement
        context['departure_movement'] = departure_movement
        return context


class HandlingServiceSelect2View(DodPermissionsMixin, HandlingServiceSelect2Mixin):
    pass


class HandlingServiceNoteView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestServices
    form_class = HandlingServiceInternalNoteForm

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        missions = user_position.managed_sfr_list
        return HandlingRequestServices.objects.filter(
            movement__request__in=missions)

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Service Request Note',
            'icon': 'fa-note',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestUpdateTailNumberView(DodPermissionsMixin, BSModalUpdateView):
    """
    View update Handling Request tail number and set required state for included services.
    """
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateTailNumberForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        return user_position.managed_sfr_list

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update tail number for {obj.callsign}',
            'icon': 'fa-id-card',
            'text': f'Submitting new tail number will reset services confirmation state to unconfirmed',
            'form_id': 'update_tail_number_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
            'js_scripts': [
                static('js/sfr_update_tail_number.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestAircraftCreateView(DodPermissionsMixin, HandlingRequestAircraftCreateMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        user_position = getattr(self.request, 'dod_selected_position')
        self.organisation = user_position.organisation


class HandlingRequestUpdateAircraftTypeView(DodPermissionsMixin, UpdateAircraftTypeMixin):
    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        return user_position.managed_sfr_list


class HandlingRequestAircraftOnGroundView(DodPermissionsMixin, GetHandlingRequestMixin, HandlingRequestAogMixin):
    pass


class HandlingRequestAircraftServiceableView(DodPermissionsMixin, HandlingRequestAircraftServiceableMixin):
    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        qs = HandlingRequestMovement.objects.filter(request__in=user_position.managed_sfr_list)
        return qs


class HandlingRequestUpdateMovementView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_update_movement.html'
    model = HandlingRequestMovement
    form_class = HandlingRequestUpdateMovementDetailsForm

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        qs = HandlingRequestMovement.objects.filter(request__in=user_position.managed_sfr_list)
        return qs

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update {obj.direction} Movement Details',
            'icon': 'fa-sticky-note',
            'form_id': 'sfr_update_movement',
            'text': f'Updating this details services, fuel and parking booking confirmations will be <b>reset</b>.',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestCancelView(DodPermissionsMixin, GetHandlingRequestMixin, HandlingRequestCancelMixin):
    missions_filer_managed = True


class HandlingRequestUpdateRecurrenceView(DodPermissionsMixin, UpdateRecurrenceMixin):
    pass


class HandlingRequestCancelRecurrenceView(DodPermissionsMixin, CancelRecurrenceMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.recurrence = get_object_or_404(HandlingRequestRecurrence, pk=self.kwargs['pk'])

        missions = self.person_position.get_sfr_list(managed=True)
        if self.recurrence.handling_requests.first() not in missions:
            raise Http404


class HandlingRequestDetailsPDFView(DodPermissionsMixin, View):
    """
    This view return S&F Request Details PDF file
    """
    def get(self, request, *args, **kwargs):
        user_position = getattr(self.request, 'dod_selected_position')
        missions = user_position.managed_sfr_list
        handling_request = missions.include_payload_data().get(pk=self.kwargs['pk'])
        document_file = generate_handling_request_pdf(handling_request)
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={document_file["name"]}'
        return response


class HandlingRequestCallsignUpdateView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestCallsignUpdateForm

    def get_queryset(self):
        return self.person_position.managed_sfr_list

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Mission Callsign',
            'icon': 'fa-fighter-jet',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestMissionNumberUpdateView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = HandlingRequestMissionNumberUpdateForm

    def get_queryset(self):
        return self.person_position.managed_sfr_list

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Mission Number',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class HandlingRequestReinstateView(DodPermissionsMixin, GetHandlingRequestMixin, BSModalFormView):
    template_name = 'handling_request/_modal_reinstate.html'
    form_class = HandlingRequestReinstateForm
    missions_filer_managed = True

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if hasattr(self, 'handling_request'):
            kwargs.update({'handling_request': self.handling_request})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.handling_request.arrival_movement.date <= timezone.now():
            text = f'Servicing & Fueling Request have <b>movement dates in past</b>, please set new ' \
                   'dates and confirm reinstating.'
        else:
            text = f'Please confirm Servicing & Fueling Request reinstating.'

        metacontext = {
            'title': 'Reinstate Servicing & Fueling Request',
            'icon': 'fa-trash-restore',
            'text': text,
            'action_button_text': 'Reinstate',
            'action_button_class': 'btn-secondary',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        form.save()
        messages.success(self.request, f'Servicing & Fueling Request has been reinstated')
        return super().form_valid(form)


class HandlingRequestPayloadUpdateView(DodPermissionsMixin, HandlingRequestPayloadMixin):

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        user_position = getattr(self.request, 'dod_selected_position')
        self.handling_request = user_position.managed_sfr_list.filter(pk=self.kwargs['pk']).first()


class HandlingRequestConversationCreateView(DodPermissionsMixin, GetHandlingRequestMixin,
                                            HandlingRequestConversationCreateMixin):
    pass
