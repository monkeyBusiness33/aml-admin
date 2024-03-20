import json

from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, F, Q, IntegerField, Case, When, BooleanField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import TemplateView, DetailView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_organisation_status_badge
from handling.forms.handling_service import HandlingServiceForm, HandlingServiceTagsForm
from handling.models import HandlingService, HandlingServiceAvailability, HandlingServiceOrganisationSpecific
from organisation.models import Organisation
from user.mixins import AdminPermissionsMixin


class HandlingServicesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = HandlingService
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['handling.p_view']

    def get_initial_queryset(self, request=None):
        return self.model.objects.active().filter(
            (Q(is_dla=False) & Q(is_dla_v2=False)) |
            (Q(is_dla=True) & Q(is_dla_v2=False) & Q(is_spf_v2_non_dla=True)),
            custom_service_for_request__isnull=True,
        )

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Service Name', 'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'is_active', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'created_at',  'visible': True, 'searchable': False, 'choices': False, },
        {'name': 'actions', 'title': 'Actions', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")
        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:handling_service', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit text-primary',
                                                button_active=self.request.user.has_perm('handling.p_view'),
                                                button_modal=False,
                                                modal_validation=False)
        del_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                    'admin:handling_service_delete', kwargs={'pk': obj.pk}),
                                               button_class='ml-2 text-danger fa-trash-alt',
                                               button_active=self.request.user.has_perm('handling.p_update'),
                                               button_modal=True,
                                               modal_validation=False)
        row['actions'] = edit_btn + del_btn
        return


class HandlingServicesListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['handling.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add Handling Service',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:handling_services_add'),
             'button_modal': True,
             'button_modal_size': '#modal-lg',
             'button_perm': self.request.user.has_perm('handling.p_create')},
        ]

        metacontext = {
            'title': 'Handling Services (Non-DLA)',
            'page_id': 'handling_services_list',
            'page_css_class': 'clients_list',
            'datatable_uri': 'admin:handling_services_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class HandlingServiceCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'handling_service_edit.html'
    model = HandlingService
    form_class = HandlingServiceForm
    success_url = reverse_lazy('admin:handling_services')
    permission_required = ['handling.p_create']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create Handling Service',
            'icon': 'fa-cogs',
        }

        context['metacontext'] = metacontext
        return context


class HandlingServiceEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_service_edit.html'
    model = HandlingService
    form_class = HandlingServiceForm
    success_message = 'Service details has been updated'
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['service'] = self.get_object()
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Handling Service',
            'icon': 'fa-cogs',
        }

        context['metacontext'] = metacontext
        return context


class HandlingServiceAvailabilityAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['handling.p_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.airport().filter(
            hs_availability__service_id=self.kwargs['pk'],
        ).annotate(
            arrival_count=Coalesce(Count(F('hs_availability'),
                                         filter=Q(hs_availability__direction='ARRIVAL',
                                                  hs_availability__service_id=self.kwargs['pk']),
                                         output_field=IntegerField()), 0),
            arrival=Case(
                When(arrival_count__gte=1, then=True),
                default=False,
                output_field=BooleanField()),
            departure_count=Coalesce(Count(F('hs_availability'),
                                           filter=Q(hs_availability__direction='DEPARTURE',
                                                    hs_availability__service_id=self.kwargs['pk']),
                                           output_field=IntegerField()), 0),
            departure=Case(
                When(departure_count__gte=1, then=True),
                default=False,
                output_field=BooleanField()),
        ).all()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'airport', 'title': 'Airport', 'foreign_field': 'airport_details__icao_code', 'visible': True, },
        {'name': 'on_arrival', 'title': 'On Arrival', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False},
        {'name': 'on_departure', 'title': 'On Departure', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False},
        {'name': 'actions', 'title': 'Actions', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['airport'] = f'{obj.details.registered_name} ({obj.airport_details.icao_iata})'
        handling_service_id = self.kwargs['pk']

        def get_icon(availability):
            if availability:
                btn_class = 'fa-check-circle text-success'
                btn_popup = 'Disable Service'
            else:
                btn_class = 'fa-ban text-danger'
                btn_popup = 'Enable Service'

            return {'btn_class': btn_class, 'btn_popup': btn_popup}

        row['on_arrival'] = get_datatable_actions_button(button_text='',
                                                         button_url=reverse_lazy(
                                                             'admin:handling_service_availability', kwargs={
                                                                 'service': handling_service_id,
                                                                 'action': 'arrival',
                                                                 'airport': obj.pk
                                                             }),
                                                         button_class=get_icon(obj.arrival)['btn_class'],
                                                         button_popup=get_icon(obj.arrival)['btn_popup'],
                                                         button_active=self.request.user.has_perm('handling.p_update'),
                                                         button_modal=True,
                                                         modal_validation=False)

        row['on_departure'] = get_datatable_actions_button(button_text='',
                                                           button_url=reverse_lazy(
                                                               'admin:handling_service_availability', kwargs={
                                                                   'service': handling_service_id,
                                                                   'action': 'departure',
                                                                   'airport': obj.pk
                                                               }),
                                                           button_class=get_icon(obj.departure)['btn_class'],
                                                           button_popup=get_icon(obj.departure)['btn_popup'],
                                                           button_active=self.request.user.has_perm(
                                                               'handling.p_update'),
                                                           button_modal=True,
                                                           modal_validation=False)

        del_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                   'admin:handling_service_availability', kwargs={
                                                       'service': handling_service_id,
                                                       'action': 'delete',
                                                       'airport': obj.pk
                                                       }),
                                               button_class='ml-2 text-danger fa-trash-alt',
                                               button_active=self.request.user.has_perm('handling.p_update'),
                                               button_modal=True,
                                               modal_validation=False)
        row['actions'] = del_btn
        return


class HandlingServiceDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'handling_service.html'
    model = HandlingService
    context_object_name = 'service'
    permission_required = ['handling.p_view']


class HandlingServiceAvailabilityUpdateView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_valid(self, form, *args, **kwargs):
        airport = Organisation.objects.airport().get(pk=self.kwargs['airport'])
        service = HandlingService.objects.get(pk=self.kwargs['service'])
        action = self.kwargs['action']

        if action == 'arrival':
            q = Q(direction_id='ARRIVAL')
            direction_code = 'ARRIVAL'
        elif action == 'departure':
            q = Q(direction_id='DEPARTURE')
            direction_code = 'DEPARTURE'
        else:
            q = Q()
            direction_code = None

        availability = HandlingServiceAvailability.objects.filter(
            q,
            airport=airport,
            service=service,
        )

        if availability.exists():
            availability.delete()

        elif not availability.exists():
            HandlingServiceAvailability.objects.create(
                airport=airport,
                service=service,
                direction_id=direction_code
            )

        messages.success(self.request, f'{service} updated successfully')

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        airport = Organisation.objects.airport().get(pk=self.kwargs['airport'])
        service = HandlingService.objects.get(pk=self.kwargs['service'])
        action = self.kwargs['action']

        if action == 'arrival':
            q = Q(direction_id='ARRIVAL')
        elif action == 'departure':
            q = Q(direction_id='DEPARTURE')
        else:
            q = Q()

        availability = HandlingServiceAvailability.objects.filter(
            q,
            airport=airport,
            service=service,
        ).first()

        if availability and action == 'delete':
            metacontext = {
                'title': f'Delete {service} for {airport.airport_details.icao_code}',
                'icon': 'fa-trash-alt',
                'text': f'Are you sure about <span class="text-danger">detach</span> '
                        f'{airport.airport_details.icao_code} from {service} availability.',
                'action_button_text': 'Delete',
                'action_button_class': 'btn-danger',
            }

        elif availability:

            metacontext = {
                'title': f'Disable {service} on {action} for {airport.airport_details.icao_code}',
                'icon': 'fa-ban',
                'text': f'Are you sure about disable {service} on {action} for {airport.airport_details.icao_code}',
                'action_button_text': 'Disable',
                'action_button_class': 'btn-danger',
            }
        else:
            metacontext = {
                'title': f'Enable {service} on {action} for {airport.airport_details.icao_code}',
                'icon': 'fa-check',
                'text': f'Are you sure about enable {service} on {action} for {airport.airport_details.icao_code}',
                'action_button_text': 'Enable',
                'action_button_class': 'btn-success',
            }

        context['metacontext'] = metacontext
        return context


class HandlingServiceDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    model = HandlingService
    success_message = 'Success: Handling Service has been deleted'
    success_url = reverse_lazy('admin:handling_services')
    permission_required = ['handling.p_update']

    service = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.service = get_object_or_404(HandlingService, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Handling Service',
            'icon': 'fa-delete',
            'text': f'Are you sure about to delete Handling Service "{self.service}"?',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Delete',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if self.service.is_used:
                self.service.deleted_at = timezone.now()
                self.service.save()
            else:
                self.service.delete()
        return super().form_valid(form)


class HandlingServiceTagsView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingService
    form_class = HandlingServiceTagsForm
    success_message = 'Handling Service tags updated successfully'
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Handling Service Tags',
            'icon': 'fa-tags',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        handling_service = self.get_object()
        response = super().form_valid(form)
        # Reassign default tags even if it removed by the user
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            from ..utils.tags import update_handling_service_default_tags
            update_handling_service_default_tags(handling_service)

        return response


class HandlingServiceOrganisationsAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = HandlingServiceOrganisationSpecific
    search_values_separator = '+'
    permission_required = ['handling.p_view']

    def get_initial_queryset(self, request=None):
        return HandlingServiceOrganisationSpecific.objects.filter(
            service_id=self.kwargs['handling_service_id'])

    column_defs = [
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'registered_name', 'title': 'Registered Name',
         'foreign_field': 'organisation__details__registered_name', 'visible': True,
         'className': 'organisation_reg_name', },
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'organisation__details__trading_name',
         'visible': True, },
        {'name': 'type', 'title': 'Operator Type', 'foreign_field': 'organisation__operator_details__type__name',
         'visible': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        user = self.request.user
        if user.has_perm('organisation.p_view'):
            row['registered_name'] = f'<span data-url="{obj.organisation.get_absolute_url()}" \
                >{obj.organisation.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.organisation.operational_status)
        return
