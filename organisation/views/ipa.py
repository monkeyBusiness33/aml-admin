from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from ajax_datatable.views import AjaxDatatableView
from django.views.generic import TemplateView

from core.mixins import CustomAjaxDatatableView
from organisation.forms import IpaLocationsFormSet
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import IpaLocation, Organisation, IpaDetails
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin
from core.utils.datatables_functions import get_datatable_organisation_status_badge, get_datatable_badge
import json


class IpaListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = IpaLocation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return IpaLocation.objects.with_airport_details()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name',
         'foreign_field': 'organisation__details__registered_name', 'visible': True, 'className': 'ipa_link'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'organisation__details__trading_name',
         'visible': True},
        {'name': 'parent_org', 'title': 'Parent Organisation',
         'foreign_field': 'organisation__details__department_of__details__registered_name', },
        {'name': 'airport_name', 'title': 'Airport Name',
         'foreign_field': 'location__details__registered_name',
         'visible': True, 'choices': False, 'className': 'ipa_airport_link'},
        {'name': 'icao_iata', 'title': 'ICAO / IATA',
         'visible': True, 'choices': False, 'className': 'ipa_airport_link'},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'organisation__details__country__name',
            'visible': True, 'choices': False, },
        {'name': 'fuel_available', 'title': 'Fuel Available', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = (f'<span data-url="{obj.organisation.get_absolute_url()}">'
                                  f'{obj.organisation.full_repr}</span>')
        row['airport_name'] = (f'<span data-url="{obj.location.get_absolute_url()}">'
                               f'{obj.location.details.registered_name}</span>')

        row['fuel_available'] = ''.join([get_datatable_badge(
            badge_text=fuel_type,
            badge_class='bg-gray-600 p-1 me-1',
        ) for fuel_type in obj.fuel_types_names])

        row['status'] = get_datatable_organisation_status_badge(obj.organisation.operational_status)
        return


class IpaListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Into-Plane Agent',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:ipa_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Into-Plane Agents',
            'page_id': 'ipa_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:ipas_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class IpaDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.ipa()


class IpaLocationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    initial_order = []
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.filter(
            Q(ipa_locations_here__organisation_id=self.kwargs['ipa_id']) |
            Q(service_provider_locations__delivery_location_id=self.kwargs['ipa_id'])
        )
        return qs

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'type', 'title': 'Type', 'foreign_field': 'details__type__name',
            'visible': True, 'searchable': False, 'width': '300px'},
        {'name': 'airport_location', 'title': 'Airport / Location', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'fuel_available', 'title': 'Fuel Types Dispensed', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'location_email', 'title': 'Location Email', 'visible': True,
            'searchable': False, 'orderable': False, },
        {'name': 'location_phone', 'title': 'Location Phone', 'visible': True,
            'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        if obj.details.type.id == 8:
            row['airport_location'] = f'{obj.airport_details.icao_iata}'
            ipa_location = IpaLocation.objects.filter(organisation_id=self.kwargs['ipa_id'],
                                                      location_id=obj.pk).first()
            row['fuel_available'] = ipa_location.location_fuel_types_badges
            row['location_email'] = ipa_location.location_email or ''
            row['location_phone'] = ipa_location.location_phone or ''
        elif obj.details.type.id == 1002:
            row['airport_location'] = f'{obj.details.registered_and_trading_name}'
            row['fuel_available'] = ''
            row['location_email'] = ''
            row['location_phone'] = ''
        return


class IpaCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'ipa_edit.html'
    permission_required = ['organisation.change_ipa']

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        return self.render_to_response({
            'organisation': organisation,
            'ipa_locations_formset': IpaLocationsFormSet(
                organisation=organisation,
                prefix='ipa_locations_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        ipa_locations_formset = IpaLocationsFormSet(request.POST or None,
                                                    organisation=organisation,
                                                    prefix='ipa_locations_formset_pre')

        # Process only if ALL forms are valid
        if all([
            ipa_locations_formset.is_valid(),
        ]):
            # Add IPA Details
            ipa_details, _ = IpaDetails.objects.get_or_create(organisation=organisation)

            # Save IPA Locations
            instances = ipa_locations_formset.save(commit=False)
            for instance in instances:
                instance.organisation = organisation
            ipa_locations_formset.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'ipa_locations_formset': ipa_locations_formset,
            })
