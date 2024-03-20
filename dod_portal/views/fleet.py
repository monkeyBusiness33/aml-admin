import json
from django.views.generic import TemplateView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalFormView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax
from ajax_datatable.views import AjaxDatatableView
from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button
from dod_portal.mixins import DodPermissionsMixin
from aircraft.models import Aircraft
from aircraft.forms import AircraftForm


class AircraftCreateView(DodPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = Aircraft
    form_class = AircraftForm
    success_message = 'Aircraft created successfully'
    permission_required = ['dod_planners']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'organisation': self.person_position.organisation})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Aircraft',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context


class AircraftEditView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Aircraft
    form_class = AircraftForm
    success_message = 'Aircraft updated successfully'
    permission_required = ['dod_planners']

    def get_queryset(self):
        return Aircraft.objects.filter(
            details__operator=self.person_position.organisation,
        )

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Aircraft Details',
            'icon': 'fa-edit',
        }

        context['metacontext'] = metacontext
        return context


class AircraftDetachView(DodPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    success_message = 'Aircraft removed successfully'
    permission_required = ['dod_planners']

    def get_queryset(self):
        return Aircraft.objects.filter(
            details__operator=self.person_position.organisation,
        )

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Remove Aircraft',
            'icon': 'fa-trash',
            'text': 'Remove Aircraft from the organisation profile?',
            'action_button_text': 'Remove',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        aircraft = Aircraft.objects.get(
            pk=self.kwargs['pk'],
            details__operator=self.person_position.organisation,
        )
        aircraft_details = getattr(aircraft, 'details')

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            aircraft_details.operator = None
            aircraft_details.source = 'DoD'
            aircraft_details.save()
            messages.success(self.request, self.success_message)

        return super().form_valid(form)


class DodFleetAjaxView(DodPermissionsMixin, AjaxDatatableView):
    model = Aircraft
    search_values_separator = '+'
    permission_required = ['dod_planners']

    def get_initial_queryset(self, request=None):
        qs = Aircraft.objects.filter(
            details__operator_id=self.person_position.organisation)
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'asn', 'title': 'ASN', 'visible': True},
        {'name': 'registration', 'title': 'Registration', 'foreign_field': 'details__registration', 'visible': True},
        {'name': 'type', 'title': 'Aircraft Type', 'foreign_field': 'type__model', 'visible': True},
        {'name': 'pax_seats', 'visible': True},
        {'name': 'yom', 'visible': True},
        {'name': 'homebase', 'title': 'Homebase', 'foreign_field': 'details__homebase__airport_details__icao_code',
         'visible': True},
        {'name': 'is_decommissioned', 'visible': True},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['type'] = f'{obj.type}'
        homebase_airport = getattr(obj.details.homebase, 'airport_details', None)
        if homebase_airport:
            homebase = homebase_airport.icao_iata
        else:
            homebase = ''
        row['homebase'] = homebase

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'dod:fleet_edit', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=True,
                                                button_modal=True,
                                                modal_validation=True)
        del_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                   'dod:fleet_remove', kwargs={'pk': obj.pk}),
                                               button_class='fa-trash text-danger',
                                               button_active=True,
                                               button_modal=True,
                                               modal_validation=False)

        row['actions'] = edit_btn + del_btn
        return


class DodFleetListView(DodPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['dod_planners']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Aircraft',
             'button_icon': 'fa-plus',
             'button_url': reverse('dod:fleet_create'),
             'button_modal': True,
             'button_perm': True},
        ]

        metacontext = {
            'title': 'Aircraft Fleet',
            'page_id': 'dod_aircraft_fleet',
            'page_css_class': '',
            'datatable_uri': 'dod:fleet_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context
