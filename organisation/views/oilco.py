import json

from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalUpdateView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView

from core.utils.datatables_functions import get_datatable_oilco_fuel_badges, get_datatable_organisation_status_badge
from dla_scraper.utils.scraper import reconcile_org_name
from organisation.forms import OilcoFuelTypesForm, OrganisationDetailsForm, OrganisationRestictedForm, \
    OilcoDetailsForm, OrganisationAddressFormSet
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OilcoFuelType, OrganisationDetails, OrganisationRestricted, OilcoDetails
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class OilcoListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.oilco()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'fuel_types', 'title': 'Fuel Types', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'contract', 'title': 'Contract?', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['fuel_types'] = get_datatable_oilco_fuel_badges(obj.oilco_fuel_types.all())
        row['contract'] = ''
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class OilcoListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Oil Company',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:oilco_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Oil Companies',
            'page_id': 'oilco_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:oilcos_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class OilcoDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.oilco()


class OilcoFuelTypesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OilcoFuelType
    search_values_separator = '+'
    initial_order = []
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = OilcoFuelType.objects.filter(
            organisation_id=self.kwargs['oilco_id']
        )
        return qs

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False,
            'orderable': True, 'width': '10px'},
        {'name': 'fuel_type_name', 'title': 'Fuel Type', 'foreign_field': 'fuel_type__name',
            'visible': True, 'searchable': True, },
        {'name': 'fuel_type_nato_code', 'title': 'NATO Code', 'foreign_field': 'fuel_type__nato_code',
            'visible': True, 'searchable': True},
    ]


class OilcoFuelTypesUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Organisation
    form_class = OilcoFuelTypesForm
    pk_url_kwarg = "oilco_id"
    success_message = 'Fuel Types updated successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Update Oil Company Fuel Types Produced',
            'text': 'Using this dialog you can update current oil company produced fuel types',
            'icon': 'fa-gas-pump',
        }

        context['metacontext'] = metacontext
        return context


class OilcoEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'oilco_edit.html'

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        oilco_details = getattr(organisation, 'oilco_details', OilcoDetails())

        return self.render_to_response({
            'organisation': organisation,
            'oilco_fuel_types_form': OilcoFuelTypesForm(
                request=self.request,
                instance=organisation,
                prefix='oilco_fuel_types_form_pre',),
            'oilco_details_form': OilcoDetailsForm(
                instance=oilco_details,
                prefix='oilco_details_form_pre',),
            })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        oilco_details = getattr(organisation, 'oilco_details', OilcoDetails())

        oilco_fuel_types_form = OilcoFuelTypesForm(request.POST or None,
                                                   request=self.request,
                                                   instance=organisation,
                                                   prefix='oilco_fuel_types_form_pre')

        oilco_details_form = OilcoDetailsForm(request.POST or None,
                                              instance=oilco_details,
                                              prefix='oilco_details_form_pre')

        # Process only if ALL forms are valid
        if all([
            oilco_details_form.is_valid(),
            oilco_fuel_types_form.is_valid(),
        ]):
            oilco_details = oilco_details_form.save(commit=False)
            oilco_details.organisation = organisation
            oilco_details.save()

            # Save oilco_fuel_types_form objects directly without form saving as we have already created organisation
            oilco_fuel_types = oilco_fuel_types_form.cleaned_data['oilco_fuel_types']
            organisation.oilco_fuel_types.set(oilco_fuel_types, clear=True)

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'oilco_details_form': oilco_details_form,
                'oilco_fuel_types_form': oilco_fuel_types_form,
                })
