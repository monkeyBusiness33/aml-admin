from datetime import date
import json
import logging

from ajax_datatable.views import AjaxDatatableView
from django.db.models import Q
from django.http import HttpResponseGone, HttpResponseRedirect
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import RedirectView, TemplateView

from core.models import Tag
from core.utils.datatables_functions import get_datatable_badge, get_datatable_organisation_status_badge
from organisation.forms import FuelResellerDetailsForm
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation
from organisation.views.base import OrganisationCreateEditMixin
from pricing.models import FuelPricingMarket, FuelPricingMarketPld
from pricing.utils import get_datatable_agreement_locations_list
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin


class FuelResellerListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.fuel_seller()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'type', 'title': 'Type', 'foreign_field': 'details__type__name', 'visible': True,
         'choices': False, 'autofilter': True, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class FuelResellerListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Fuel Reseller',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:fuel_reseller_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Fuel Sellers',
            'page_id': 'fuel_resellers_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:fuel_resellers_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class FuelResellerCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'fuel_reseller_edit.html'

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        return self.render_to_response({
            'organisation': organisation,
            'fuel_reseller_details_form': FuelResellerDetailsForm(
                organisation=organisation,
                prefix='fuel_reseller_details_form_pre',),
        })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        organisation_details = organisation.details
        organisation_details.pk = None
        organisation_details.updated_by = getattr(self, 'person')
        organisation_details.change_effective_date = date.today()

        fuel_reseller_details_form = FuelResellerDetailsForm(request.POST or None,
                                                             organisation=organisation,
                                                             prefix='fuel_reseller_details_form_pre')

        # Process only if ALL forms are valid
        if all([
            fuel_reseller_details_form.is_valid(),
        ]):
            # Save Organisation details
            if fuel_reseller_details_form.cleaned_data['is_fuel_agent']:
                organisation_details.type_id = 13
            else:
                organisation_details.type_id = 2

            organisation_details.save()
            organisation.details = organisation_details
            organisation.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
            })


class FuelResellerDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.fuel_seller()


class FuelSellerMarketPricingLocationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    initial_order = [['latest_expiry_date', 'desc']]
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view', 'pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': self.model.objects.get(id=pk),
            'table_name': 'fuel_seller_market_pricing_locations_sublist',
            'table_url': reverse_lazy('admin:fuel_seller_market_pricing_locations_sublist_ajax', kwargs={
                'pk': self.kwargs['pk'],
                'location_pk': pk
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        return self.model.objects.airport().with_market_pld_details(self.kwargs['pk'])

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'location', 'title': 'Location ICAO', 'foreign_field': 'airport_details__icao_code',
         'className': 'url_source_col parent-row', },
        {'name': 'fuel_types', 'title': 'Fuel Types', 'orderable': False, },
        {'name': 'latest_expiry_date', 'title': 'Latest Pricing Expiry Date', },
    ]

    def customize_row(self, row, obj):
        has_children = len(obj.active_market_pricing_plds) > 1
        url = reverse_lazy("admin:fuel_pricing_market_document_details",
                           kwargs={"pk": obj.active_market_pricing_plds[0]}) \
            if not has_children else ''
        row['location'] = f'<span class="{"has_children" if has_children else ""}"' \
                          f' data-url={url}>{row["location"]}</span>'

        fuel_types_str = ''

        for fuel_type in sorted(obj.fuel_types):
            fuel_types_str += get_datatable_badge(
                badge_text=fuel_type,
                badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                tooltip_enable_html=True
            )

        row['fuel_types'] = f'<div class="d-flex flex-wrap">{fuel_types_str}</div>'


class FuelSellerMarketPricingLocationsSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelPricingMarketPld
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        supplier_pk = self.kwargs['pk']
        location_pk = self.kwargs['location_pk']
        plds_with_active_market_pricing_qs = FuelPricingMarket.objects.filter(
            Q(supplier_pld_location__location=location_pk)
            & Q(supplier_pld_location__pld__supplier=supplier_pk)
            & Q(deleted_at__isnull=True) & Q(price_active=True)
        ).values('supplier_pld_location__pld').distinct()

        qs = FuelPricingMarketPld.objects.filter(
            Q(pk__in=plds_with_active_market_pricing_qs)
        )

        return qs

    column_defs = [
        # Note: using render_row_tools here, else I can't make placeholder data to show up in the first column
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'pld_name', 'title': 'PLD Title', 'className': 'url_source_col', },
        {'name': 'dummy_1', 'title': 'Dummy', 'placeholder': True, },
        {'name': 'fuel_types', 'title': 'Fuel Types', 'placeholder': True },
        {'name': 'dummy_2', 'title': 'Dummy', 'placeholder': True, },
        {'name': 'dummy_3', 'title': 'Dummy', 'placeholder': True, },
        {'name': 'latest_expiry_date', 'title': 'Latest Pricing Expiry Date', },
    ]

    def customize_row(self, row, obj):
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        url = reverse_lazy("admin:fuel_pricing_market_document_details", kwargs={"pk": obj.pk})
        row['pld_name'] = f'<span data-url={url}>{row["pld_name"]}</span>'

        fuel_types_str = ''

        for fuel_type in sorted(obj.fuel_types):
            fuel_types_str += get_datatable_badge(
                badge_text=fuel_type,
                badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                tooltip_enable_html=True
            )

        row['fuel_types'] = f'<div class="d-flex flex-wrap">{fuel_types_str}</div>'
        row['latest_expiry_date'] = f'<div class="d-flex flex-wrap">{obj.latest_expiry_date}</div>'


class FuelSellerAgreementsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreement
    search_values_separator = '+'
    initial_order = [['validity', 'desc']]
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view', 'pricing.p_view']

    def get_initial_queryset(self, request=None):
        return self.model.objects.filter(supplier__pk=self.kwargs['pk'])

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'reference', 'title': 'Reference', 'placeholder': True, 'className': 'url_source_col' },
        {'name': 'validity', 'title': 'Validity Period', 'searchable': False, },
        {'name': 'locations', 'title': 'Locations Covered', 'orderable': False, },
    ]

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_val = column_link.search_value
                if column_link.name == 'reference':
                    qs = qs.filter(Q(pk__icontains=search_val) | Q(aml_reference__icontains=search_val))
                elif column_link.name == 'locations':
                    qs = qs.filter(Q(pricing_formulae__location__airport_details__icao_code__icontains=search_val)
                                   | Q(pricing_manual__location__airport_details__icao_code__icontains=search_val))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs.distinct()

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'reference' in orders:
            if 'ASC' in str(params['orders'][0]):
                return qs.order_by('pk')
            else:
                return qs.order_by('-pk')
        elif 'validity' in orders:
            if 'ASC' in str(params['orders'][0]):
                return qs.order_by('start_date', 'end_date')
            else:
                return qs.order_by('-start_date', '-end_date')
        else:
            return qs.order_by(*[order.get_order_mode() for order in params['orders']])

    def customize_row(self, row, obj):
        row['reference'] = f'<span data-url="{obj.get_absolute_url()}">{obj.datatable_str}</span>'
        row['validity'] = obj.validity_range_str
        row['locations'] = get_datatable_agreement_locations_list(obj)
        return


class AddFuelSellerTagView(AdminPermissionsMixin, RedirectView):
    """
    This view marks the Organisation as a Fuel Seller and redirects back to organisation details page.
    """
    permission_required = ['core.p_contacts_update']
    logger = logging.getLogger("django.request")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.url = reverse_lazy('admin:organisation_details', kwargs={'pk': kwargs['pk']})

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)

        # Mark the organisation as Fuel Seller
        organisation = get_object_or_404(Organisation, pk=kwargs['pk'])
        organisation.organisation_restricted.is_fuel_seller = True
        organisation.organisation_restricted.save()
        is_fuel_seller_tag_name = 'Fuel Seller'
        tag, _ = Tag.objects.get_or_create(name=is_fuel_seller_tag_name, is_system=True)
        organisation.tags.add(tag, through_defaults=None)

        if url:
            return HttpResponseRedirect(url)
        else:
            self.logger.warning(
                "Gone: %s", request.path, extra={"status_code": 410, "request": request}
            )
            return HttpResponseGone()
