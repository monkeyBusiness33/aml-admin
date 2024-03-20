import json

from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView

from aircraft.forms import AircraftForm
from aircraft.models import Aircraft
from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_organisation_status_badge
from dla_scraper.utils.scraper import reconcile_org_name
from organisation.forms import OrganisationDetailsForm, OrganisationLogoMottoForm, OrganisationRestictedForm, \
    OrganisationAircraftTypesForm, OperatorDetailsForm, OrganisationAddressFormSet, OperatorPreferredGroundHandlerForm
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OrganisationDetails, OrganisationLogoMotto, OrganisationRestricted, \
    OperatorDetails, OperatorPreferredGroundHandler
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class AircraftOperatorsListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    # QuerySet Optimizations
    disable_queryset_optimization_only = False

    def get_initial_queryset(self, request=None):
        return Organisation.objects.aircraft_operator()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True, },
        {'name': 'operator_type', 'title': 'Operator Type', 'foreign_field': 'operator_details__type__name',
         'visible': True, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class AircraftOperatorsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add Aircraft Operator',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:aircraft_operators_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Aircraft Operators',
            'page_id': 'aircraft_operators_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:aircraft_operators_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class AircraftOperatorCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'aircraft_operator_edit.html'

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        operator_details = getattr(
            organisation, 'operator_details', OperatorDetails())

        return self.render_to_response({
            'organisation': organisation,

            'organisation_aircraft_types_form': OrganisationAircraftTypesForm(
                instance=organisation,
                prefix='organisation_aircraft_types_form_pre'
            ),

            'operator_details_form': OperatorDetailsForm(
                instance=operator_details,
                prefix='operator_details_form_pre',),
            })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        operator_details = getattr(organisation, 'operator_details', OperatorDetails())

        organisation_aircraft_types_form = OrganisationAircraftTypesForm(request.POST or None,
                                                                         instance=organisation,
                                                                         prefix='organisation_aircraft_types_form_pre')

        operator_details_form = OperatorDetailsForm(request.POST or None,
                                                    instance=operator_details,
                                                    prefix='operator_details_form_pre')

        # Process only if ALL forms are valid
        if all([
            organisation_aircraft_types_form.is_valid(),
            operator_details_form.is_valid(),
        ]):

            # Save Organisation details
            organisation = organisation_aircraft_types_form.save(commit=False)
            organisation_aircraft_types_form.save_m2m()

            operator_details = operator_details_form.save(commit=False)
            operator_details.organisation = organisation
            operator_details.save()

            # Set is_authorising_person value for organisation's people
            for position in organisation.organisation_people.all():
                if position in operator_details_form.cleaned_data['authorising_people']:
                    position.is_authorising_person = True
                else:
                    position.is_authorising_person = False
                position.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'operator_details_form': operator_details_form,
            })


class AircraftOperatorDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.aircraft_operator()


#######################################################################
# Aircraft Operator Fleet section start
#######################################################################


class AircraftOperatorFleetAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Aircraft
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        if self.request.user.is_superuser:
            qs = Aircraft.objects.include_test_aircraft().filter(
                details__operator_id=self.kwargs['operator_id'])
        else:
            qs = Aircraft.objects.filter(
                details__operator_id=self.kwargs['operator_id'])

        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'registration', 'title': 'Registration', 'foreign_field': 'details__registration', 'visible': True, },
        {'name': 'type', 'title': 'Aircraft Type', 'foreign_field': 'type__model', 'visible': True, },
        {'name': 'homebase', 'title': 'Homebase', 'foreign_field': 'details__homebase__airport_details__icao_code',
         'visible': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, },
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
                                                    'admin:aircraft_edit', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                button_modal=True,
                                                modal_validation=True)

        row['actions'] = edit_btn
        return


class AircraftOperatorFleetCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = Aircraft
    form_class = AircraftForm
    success_message = 'Aircraft created successfully'
    permission_required = ['core.p_contacts_create']

    organisation = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['operator_id'])
        kwargs.update({'organisation': self.organisation})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Aircraft',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context


#######################################################################
# Aircraft Operator Preferred Handler section start
#######################################################################


class AircraftOperatorLocationPreferredHandlerAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OperatorPreferredGroundHandler
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = OperatorPreferredGroundHandler.objects.filter(
            organisation_id=self.kwargs['operator_id'],
        )
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'location', 'title': 'Airport / Location', 'foreign_field': 'location__details__registered_name',
         'visible': True, },
        {'name': 'handler', 'title': 'Preferred Ground Handler',
         'foreign_field': 'ground_handler__details__registered_name', 'visible': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['location'] = getattr(obj.location, 'full_repr')
        row['handler'] = getattr(obj.ground_handler, 'trading_and_registered_name')

        detach_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:aircraft_operator_preferred_handler_remove',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = detach_btn
        return


class OperatorPreferredGroundHandlerCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = OperatorPreferredGroundHandler
    form_class = OperatorPreferredGroundHandlerForm
    success_message = 'Preferred Handler created successfully'
    permission_required = ['core.p_contacts_update']

    organisation = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['operator_id'])
        instance = OperatorPreferredGroundHandler(organisation=self.organisation)
        kwargs.update({'instance': instance})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add Location Preferred Handler',
            'icon': 'fa-plus',
            'form_id': 'operator_preferred_ground_handler_form',
            'js_scripts': [
                static('js/operator_preferred_ground_handlers.js'),
            ],
        }

        context['metacontext'] = metacontext
        return context


class OperatorPreferredGroundHandlerDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OperatorPreferredGroundHandler
    form_class = ConfirmationForm
    success_message = 'Preferred Handler successfully removed'
    permission_required = ['core.p_contacts_update']

    organisation = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Remove Location Preferred Handler',
            'text': f'Please confirm preferred handler removal',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context
