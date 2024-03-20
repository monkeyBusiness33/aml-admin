import copy
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Exists, OuterRef, Q, Subquery
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView, DetailView
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalFormView, BSModalReadView
from bootstrap_modal_forms.mixins import is_ajax

from core.forms import ConfirmationForm
from core.models import Country
from core.utils.datatables_functions import get_datatable_actions_button
from pricing.forms import ArchivalForm, NewTaxRuleFormset, TaxForm, TaxRuleFormset, TaxSourceForm
from pricing.models import Tax, TaxApplicationMethod, TaxRatePercentage, TaxRule, TaxRuleException
from user.mixins import AdminPermissionsMixin


# Main Table
class OfficialTaxesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Country
    search_values_separator = '+'
    permission_required = ['pricing.p_view']
    initial_order = [["name", "asc"], ]
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]

    def render_row_details(self, pk, request=None):
        return render_to_string('official_taxes_list_tax_subtable.html', {
            'object': Country.objects.get(id=pk),
            'table_name': 'country_taxrule'
        })

    def get_initial_queryset(self, request=None):
        applicable_taxes = TaxRule.objects.all_taxes(OuterRef('pk'))

        latest_updated_at = applicable_taxes.order_by('-updated_at').values('updated_at')[:1]

        qs = Country.objects.all().annotate(
            updated_at=Subquery(latest_updated_at),
            has_fee_tax=Exists(applicable_taxes.filter(applies_to_fees=True)),
            has_fuel_tax=Exists(applicable_taxes.filter(applies_to_fuel=True)))

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'name', 'title': 'Country', 'placeholder': True,
            'width': '279.88px', },
        {'name': 'category', 'title': 'Category',
            'placeholder': True, 'searchable': False, 'orderable': False, 'width': '279.88px'},
        {'name': 'has_fee_tax', 'title': 'Applies to Fees?', 'placeholder': True, 'searchable': False,
         'className': 'service', 'width': '279.88px'},
        {'name': 'has_fuel_tax', 'title': 'Applies to Fuel?', 'placeholder': True, 'searchable': False,
            'className': 'fuel', 'width': '279.88px'},
        {'name': 'updated_at', 'title': 'Last Updated',
            'placeholder': True, 'width': '279.88px'},
        {'name': 'action', 'title': '', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions', 'width': "168px"},
    ]

    def customize_row(self, row, obj):
        all_taxes = TaxRule.objects.all_taxes(obj)

        if all_taxes.exists():
            child_class = 'has_children'
        else:
            child_class = ''

        row['name'] = f'<span class="{child_class}"\>{obj.name}</span>'
        row['category'] = ''

        if obj.has_fee_tax:
            row['has_fee_tax'] = '&#10003;'
        else:
            row['has_fee_tax'] = '&#10005'

        if obj.has_fuel_tax:
            row['has_fuel_tax'] = '&#10003;'
        else:
            row['has_fuel_tax'] = '&#10005'

        if obj.has_fee_tax == False and obj.has_fuel_tax == False:
            row['action'] = get_datatable_actions_button(button_text='Add Taxes',
                                                         button_url=reverse_lazy('admin:tax_creation_choice',
                                                            kwargs={'pk': obj.pk}),
                                                         button_class='btn-outline-primary p-1',
                                                         button_active=self.request.user.has_perm(
                                                            'pricing.p_create'),
                                                         button_icon='fa-plus',
                                                         button_modal=True,
                                                         modal_validation=False)
        else:
            row['action'] = get_datatable_actions_button(button_text='Update Taxes',
                                                         button_url=reverse_lazy('admin:specific_country_tax_list',
                                                            kwargs={'pk': obj.pk}),
                                                         button_class='btn-outline-primary p-1',
                                                         button_active=self.request.user.has_perm(
                                                            'pricing.p_view'),
                                                         button_icon='fa-edit',
                                                         button_modal=False)

        if obj.updated_at is not None:
            row['updated_at'] = obj.updated_at.strftime("%Y-%m-%d")
        else:
            row['updated_at'] = '--'

        return


# Page Table Caller
class OfficialTaxesListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Official Taxes',
            'page_id': 'official_taxes_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:official_taxes_ajax'
        }

        context['metacontext'] = metacontext
        return context


# Sub table
class OfficialTaxesChildrenListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRule
    search_values_separator = '+'
    permission_required = ['pricing.p_view']


    def get_initial_queryset(self, request=None):
        self.disable_queryset_optimization = True
        country = self.kwargs['pk']

        return TaxRule.objects.all_taxes(country).distinct_per_location_and_category()

    column_defs = [
        # Note: using render_row_tools here, else I can't make placeholder data to show up in the first column
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'name', 'title': 'Country', 'placeholder': True, 'width': '279px'},
        {'name': 'category_name', 'title': 'name', 'width': '279px'},
        {'name': 'any_applies_to_fees', 'title': 'Applies to Fees?',
         'className': 'service', 'width': '279px'},
        {'name': 'any_applies_to_fuel', 'title': 'Applies to Fuel?',
            'className': 'fuel', 'width': '279px'},
        {'name': 'updated_at', 'title': 'Last Updated', 'width': '279px'},
        {'name': 'actions', 'title': '', 'placeholder': True,
            'className': 'actions', 'width': "168px"},
    ]

    def sort_queryset(self, params, qs):
        # The default sorting function messes up the results completely, so we can't use it.
        # Instead, we just always sort the sublist by category and then by location.
        return qs.order_by('category_name', 'applicable_region_name', 'applicable_region_code')

    def customize_row(self, row, obj):
        row['name'] = ''

        # obj is a dictionary here rather than an object instance
        # due to use of annotate() and values() for aggregation of the qs.

        if obj['applicable_region_name']:
            row['name'] = f"{obj['applicable_region_name']} region"
        elif obj['applicable_region_code']:
            row['name'] = f"{obj['applicable_region_code']} region"

        if obj['specific_airport__airport_details__icao_code']:
            row['name'] = obj["specific_airport__airport_details__icao_code"]

        row['category_name'] = obj['category_name']

        if obj['any_applies_to_fees']:
            row['any_applies_to_fees'] = '&#10003;'
        else:
            row['any_applies_to_fees'] = '&#10005'

        if obj['any_applies_to_fuel']:
            row['any_applies_to_fuel'] = '&#10003;'
        else:
            row['any_applies_to_fuel'] = '&#10005'

        row['updated_at'] = obj['latest_update'].strftime("%Y-%m-%d")
        row['actions'] = ''

        return

# Choose tax creation
class OfficialTaxesTaxCreationChoiceView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'pricing_pages_includes/_official_taxes_form_choice_modal.html'
    form_class = ConfirmationForm
    model = Country
    permission_required = ['pricing.p_create']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Choose from the following tax types',
            'icon': 'fa-plus',
            'country': self.object
        }

        context['metacontext'] = metacontext
        return context


# List of tax rules in a specific country
class SpecificCountryTaxListView(AdminPermissionsMixin, DetailView):
    template_name = 'official_taxes_specific_country_tax_list.html'
    model = Country
    context_object_name = 'country'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        country = self.kwargs['pk']

        metacontext = {
            'country_taxes': TaxRule.objects.country_taxes(country).exists(),
            'regional_taxes': TaxRule.objects.regional_taxes(country).exists(),
            'airport_taxes': TaxRule.objects.all_taxes(country).exclude(specific_airport__isnull = True).exists()
        }

        context['metacontext'] = metacontext
        return context


# Datatable for country-level tax rules
class CountryTaxListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRule
    search_values_separator = '+'
    initial_order = [['id', "asc"]]
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('official_taxes_specific_country_tax_sublist.html', {
            'object': TaxRule.objects.get(id=pk),
            'table_name': 'country_taxes'
        })

    def get_initial_queryset(self, request=None):
        country = self.kwargs['pk']

        qs = TaxRule.objects.country_taxes(country)\
                            .filter(parent_entry = None, deleted_at__isnull = True)\
                            .exclude(specific_airport__isnull = False)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': True, 'width': '10px'},
        {'name': 'name', 'title': 'Name', 'placeholder': True, },
        {'name': 'applies_to_fuel', 'title': 'Fuel?'},
        {'name': 'applies_to_fees', 'title': 'Fees?'},
        {'name': 'rate', 'title': 'Rate', 'foreign_field': 'tax_rate_percentage__tax_percentage','placeholder': True},
        {'name': 'applicable_flight_type', 'title': 'Operator Type', 'lookup_field': '__name__icontains'},
        {'name': 'geographic_flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As'},
        {'name': 'valid_from', 'title': 'Valid From', 'lookup_field': 'valid_from__icontains'},
        {'name': 'valid_to', 'title': 'Valid To'},
        {'name': 'updated_at', 'title': 'Last Modified'},
        {'name': 'actions', 'title': '',
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions'},
    ]

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        from ajax_datatable.app_settings import TEST_FILTERS
        from ajax_datatable.views import build_column_filter
        from inspect import trace

        if TEST_FILTERS:
            trace(
                ', '.join(column_names),
                prompt='%s filtering "%s" over fields' % ('Global' if global_filtering else 'Column', search_value)
            )

        search_filters = Q()
        for column_name in column_names:

            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            # v4.0.2: we now accept multiple search values (to be ORed)
            # Split search values;
            # example: 'aaa + bbb' -> ['aaa ', ' bbb']
            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
            if column_filter:
                search_filters |= column_filter
                if TEST_FILTERS:
                    try:
                        qstest = qs.filter(column_filter)
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'name' in column_names:
            return qs.filter(Q(tax__category__name__icontains=search_value) |
                             Q(tax_rate_percentage__tax__category__name__icontains=search_value)
                             ).distinct()

        elif 'applies_to_fuel' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = False))
            else:
                return qs.filter(Q(specific_fuel__name__icontains=search_value)
                                 | Q(specific_fuel_cat__name__icontains=search_value))

        elif 'operated_as' in column_names:
            if 'commercial, private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True),
                                 Q(applies_to_private = True))
            elif 'commercial'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True))
            elif 'private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_private = True))
            else:
                return qs.filter(applies_to_private = False, applies_to_commercial = False)

        elif 'applies_to_fees' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = False))
            else:
                return qs.filter(specific_fee_category__name__icontains = search_value)

        elif 'rate' in column_names:
            # istartswith for application methods, because they can contain numbers,
            # which can return the flat rate or percentage
            if 'band(s) applicable'.startswith(search_value.lower()) or 'bands applicable'.startswith(search_value.lower()):
                return qs.filter(Q(parent_entry = None), ~Q(band_1_type = None) | ~Q(band_2_type = None))
            else:
                return qs.filter(Q(tax_rate_percentage__tax_percentage__icontains=search_value) |
                                Q(tax_rate_percentage__tax_rate__name__icontains=search_value) |
                                Q(tax_unit_rate__icontains=search_value) |
                                Q(tax_application_method__fixed_cost_application_method__name_override__istartswith=search_value) |
                                Q(tax_application_method__fuel_pricing_unit__description__istartswith=search_value)
                                ).distinct()

        elif 'valid_from' in column_names:
            return qs.filter(search_filters |
                             Q(valid_from__icontains=search_value)
                             ).distinct()

        elif 'valid_to' in column_names:
            if 'until further notice'.startswith(search_value.lower()) or 'ufn'.startswith(search_value.lower()):
                return qs.filter(Q(valid_ufn = True))

            return qs.filter(search_filters |
                             Q(valid_to__icontains=search_value)
                             ).distinct()

        elif 'updated_at' in column_names:
            return qs.filter(search_filters |
                             Q(updated_at__icontains=search_value)
                             ).distinct()
        else:
            return qs.filter(search_filters)

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]
        if 'name' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('tax_rate_percentage__tax__category')
            else:
                qs = qs.order_by('-tax_rate_percentage__tax__category')
            return qs
        elif 'operated_as' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('applies_to_private')
            else:
                qs = qs.order_by('-applies_to_private')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
            return qs

    def customize_row(self, row, obj):

        related_entries = TaxRule.objects.filter(parent_entry = obj.pk)

        if related_entries.exists() or obj.band_1_type or obj.band_2_type:
            add_class = 'has_children'
        else:
            add_class = ''

        if obj.tax:
            name = obj.tax.category.name
            row['name'] = f'<span class="{add_class}"\>{name}</span>'
        else:
            name = obj.tax_rate_percentage.tax.category.name
            row['name'] = f'<span class="{add_class}"\>{name}</span>'

        if obj.specific_fuel_cat:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel_cat})'
        elif obj.specific_fuel:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel})'

        if obj.specific_fee_category:
            row['applies_to_fees'] = f'Yes ({obj.specific_fee_category})'

        if obj.applies_to_commercial and obj.applies_to_private:
            row['operated_as'] = 'Commercial, Private'
        else:
            row['operated_as'] = 'Private' if obj.applies_to_private else 'Commercial'

        if obj.taxable_tax:
            taxable_tax = f'VAT: {obj.taxable_tax.get_rate_datatable_str()}'
        else:
            taxable_tax = ''

        row['rate'] = f'{obj.get_rate_datatable_str(inc_rate_type=True)}<br>{taxable_tax}'

        if add_class == 'has_children' or obj.band_1_type or obj.band_2_type:
            row['rate'] = 'Band(s) Applicable'

        row['valid_from'] = obj.valid_from

        if obj.valid_to:
            row['valid_to'] = obj.valid_to
        else:
            row['valid_to'] =  'Until Further Notice'

        row['updated_at'] = f'{obj.updated_at.strftime("%Y-%m-%d")}'

        view_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_details',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'country'}),
                                                        button_class='fa-eye',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_view'),
                                                        button_modal=False,
                                                        modal_validation=False)

        edit_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_edit',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'country'}),
                                                        button_class='fa-edit',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=False,
                                                        modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_delete',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk}),
                                                        button_class='fa-trash text-danger',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=True,
                                                        modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        return


# Datatable for regional tax rules
class RegionalTaxListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRule
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('official_taxes_specific_country_tax_sublist.html', {
            'object': TaxRule.objects.get(id=pk),
            'table_name': 'regional_taxes'
        })

    def get_initial_queryset(self, request=None):
        country = self.kwargs['pk']
        qs = TaxRule.objects.regional_taxes(country)\
                            .filter(parent_entry = None, deleted_at__isnull = True)\
                            .exclude(specific_airport__isnull = False)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': True, 'width': '10px'},
        {'name': 'region', 'title': 'Region', 'foreign_field': 'tax__applicable_region', 'placeholder': True},
        {'name': 'name', 'title': 'Name','placeholder': True, },
        {'name': 'applies_to_fuel', 'title': 'Fuel?'},
        {'name': 'applies_to_fees', 'title': 'Fees?'},
        {'name': 'rate', 'title': 'Rate', 'placeholder': True},
        {'name': 'applicable_flight_type', 'title': 'Operator Type', 'lookup_field': '__name__icontains'},
        {'name': 'geographic_flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As'},
        {'name': 'valid_from', 'title': 'Valid From', 'lookup_field': 'valid_from__icontains'},
        {'name': 'valid_to', 'title': 'Valid To'},
        {'name': 'updated_at', 'title': 'Last Modified'},
        {'name': 'actions', 'title': '',
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions'},
    ]

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        from ajax_datatable.app_settings import TEST_FILTERS
        from ajax_datatable.views import build_column_filter
        from inspect import trace

        if TEST_FILTERS:
            trace(
                ', '.join(column_names),
                prompt='%s filtering "%s" over fields' % ('Global' if global_filtering else 'Column', search_value)
            )

        search_filters = Q()
        for column_name in column_names:

            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            # v4.0.2: we now accept multiple search values (to be ORed)
            # Split search values;
            # example: 'aaa + bbb' -> ['aaa ', ' bbb']
            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
            if column_filter:
                search_filters |= column_filter
                if TEST_FILTERS:
                    try:
                        qstest = qs.filter(column_filter)
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'region' in column_names:
            return qs.filter(search_filters |
                             Q(tax__applicable_region__name__icontains=search_value) |
                             Q(tax__applicable_region__code__icontains=search_value) |
                             Q(tax_rate_percentage__tax__applicable_region__name__icontains=search_value) |
                             Q(tax_rate_percentage__tax__applicable_region__code__icontains=search_value)
                             ).distinct()

        elif 'applies_to_fuel' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = False))
            else:
                return qs.filter(Q(specific_fuel__name__icontains=search_value)
                                 | Q(specific_fuel_cat__name__icontains=search_value))

        elif 'operated_as' in column_names:
            if 'commercial, private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True),
                                 Q(applies_to_private = True))
            elif 'commercial'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True))
            elif 'private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_private = True))
            else:
                return qs.filter(applies_to_private = False, applies_to_commercial = False)

        elif 'applies_to_fees' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = False))
            else:
                return qs.filter(specific_fee_category__name__icontains = search_value)

        elif 'rate' in column_names:
            return qs.filter(Q(tax_rate_percentage__tax_percentage__icontains=search_value) |
                             Q(tax_unit_rate__icontains=search_value) |
                             Q(tax_application_method__fixed_cost_application_method__name_override__istartswith = search_value)
                             ).distinct()

        elif 'name' in column_names:
            return qs.filter(
                            Q(tax__category__name__icontains=search_value) |
                            Q(tax_rate_percentage__tax__category__name__icontains=search_value)
                            ).distinct()

        elif 'valid_from' in column_names:
            return qs.filter(search_filters |
                             Q(valid_from__icontains=search_value)
                             ).distinct()

        elif 'valid_to' in column_names:
            if 'until further notice'.startswith(search_value.lower()) or 'ufn'.startswith(search_value.lower()):
                return qs.filter(Q(valid_ufn = True))
            return qs.filter(search_filters |
                             Q(valid_to__icontains=search_value)
                             ).distinct()

        elif 'updated_at' in column_names:
            return qs.filter(search_filters |
                             Q(updated_at__icontains=search_value)
                             ).distinct()
        else:
            return qs.filter(search_filters)

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]
        if 'name' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('tax_rate_percentage__tax__category')
            else:
                qs = qs.order_by('-tax_rate_percentage__tax__category')
            return qs
        elif 'operated_as' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('applies_to_private')
            else:
                qs = qs.order_by('-applies_to_private')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
            return qs

    def customize_row(self, row, obj):

        related_entries = TaxRule.objects.filter(parent_entry = obj.pk)

        if related_entries.exists() or obj.band_1_type or obj.band_2_type:
            add_class = 'has_children'
        else:
            add_class = ''

        if obj.tax:
            name = obj.tax.category.name
            row['name'] = f'<span>{name}</span>'
        else:
            name = obj.tax_rate_percentage.tax.category.name
            row['name'] = f'<span>{name}</span>'

        if obj.specific_fuel_cat:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel_cat})'
        elif obj.specific_fuel:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel})'

        if obj.specific_fee_category:
            row['applies_to_fees'] = f'Yes ({obj.specific_fee_category})'

        if obj.applies_to_commercial and obj.applies_to_private:
            row['operated_as'] = 'Commercial, Private'
        else:
            row['operated_as'] = 'Private' if obj.applies_to_private else 'Commercial'

        if obj.taxable_tax:
            taxable_tax = f'VAT: {obj.taxable_tax.get_rate_datatable_str()}'
        else:
            taxable_tax = ''

        row['rate'] = f'{obj.get_rate_datatable_str(inc_rate_type=True)}<br>{taxable_tax}'

        if obj.tax:
            if obj.tax.applicable_region.name != '':
                row['region'] = obj.tax.applicable_region.name
            else:
                row['region'] = obj.tax.applicable_region.code
        else:
            if obj.tax_rate_percentage.tax.applicable_region.name != '':
                row['region'] = obj.tax_rate_percentage.tax.applicable_region.name
            else:
                row['region'] = obj.tax_rate_percentage.tax.applicable_region.code

        # Region is now the first column, so we add the 'has_children' class here where appropriate
        row['region'] = f'<span class="{add_class}">{row["region"]}</span>'

        if add_class == 'has_children' or obj.band_1_type or obj.band_2_type:
            row['rate'] = 'Band(s) Applicable'

        row['valid_from'] = obj.valid_from

        if obj.valid_to:
            row['valid_to'] = obj.valid_to
        else:
            row['valid_to'] =  'Until Further Notice'

        row['updated_at'] = f'{obj.updated_at.strftime("%Y-%m-%d")}'

        view_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_details',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'regional'}),
                                                        button_class='fa-eye',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_view'),
                                                        button_modal=False,
                                                        modal_validation=False)

        edit_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_edit',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'regional'}),
                                                        button_class='fa-edit',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=False,
                                                        modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_delete',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk}),
                                                        button_class='fa-trash text-danger',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=True,
                                                        modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        return


# Datatable for airport-specific tax rules
class AirportTaxListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRule
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('official_taxes_specific_country_tax_sublist.html', {
            'object': TaxRule.objects.get(id=pk),
            'table_name': 'airport_taxes'
        })

    def get_initial_queryset(self, request=None):
        country = self.kwargs['pk']
        qs = TaxRule.objects.all_taxes(country)\
                            .filter(parent_entry = None, deleted_at__isnull = True)\
                            .exclude(specific_airport__isnull = True)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': True, 'width': '10px'},
        {'name': 'specific_airport', 'title': 'Airport'},
        {'name': 'name', 'title': 'Name','placeholder': True},
        {'name': 'applies_to_fuel', 'title': 'Fuel?'},
        {'name': 'applies_to_fees', 'title': 'Fees?'},
        {'name': 'rate', 'title': 'Rate', 'placeholder': True},
        {'name': 'applicable_flight_type', 'title': 'Operator Type', 'lookup_field': '__name__icontains'},
        {'name': 'geographic_flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As'},
        {'name': 'valid_from', 'title': 'Valid From', 'lookup_field': 'valid_from__icontains'},
        {'name': 'valid_to', 'title': 'Valid To'},
        {'name': 'updated_at', 'title': 'Last Modified'},
        {'name': 'actions', 'title': '',
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions'},
    ]

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        from ajax_datatable.app_settings import TEST_FILTERS
        from ajax_datatable.views import build_column_filter
        from inspect import trace

        if TEST_FILTERS:
            trace(
                ', '.join(column_names),
                prompt='%s filtering "%s" over fields' % ('Global' if global_filtering else 'Column', search_value)
            )

        search_filters = Q()
        for column_name in column_names:

            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            # v4.0.2: we now accept multiple search values (to be ORed)
            # Split search values;
            # example: 'aaa + bbb' -> ['aaa ', ' bbb']
            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
            if column_filter:
                search_filters |= column_filter
                if TEST_FILTERS:
                    try:
                        qstest = qs.filter(column_filter)
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'region' in column_names:
            return qs.filter(search_filters |
                             Q(tax__applicable_region__name__icontains=search_value) |
                             Q(tax__applicable_region__code__icontains=search_value) |
                             Q(tax_rate_percentage__tax__applicable_region__name__icontains=search_value) |
                             Q(tax_rate_percentage__tax__applicable_region__code__icontains=search_value)
                             ).distinct()

        elif 'applies_to_fuel' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = False))
            else:
                return qs.filter(Q(specific_fuel__name__icontains=search_value)
                                 | Q(specific_fuel_cat__name__icontains=search_value))

        elif 'operated_as' in column_names:
            if 'commercial, private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True),
                                 Q(applies_to_private = True))
            elif 'commercial'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True))
            elif 'private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_private = True))
            else:
                return qs.filter(applies_to_private = False, applies_to_commercial = False)

        elif 'applies_to_fees' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = False))
            else:
                return qs.filter(specific_fee_category__name__icontains = search_value)

        elif 'rate' in column_names:
            return qs.filter(Q(tax_rate_percentage__tax_percentage__icontains=search_value) |
                             Q(tax_unit_rate__icontains=search_value) |
                             Q(tax_application_method__fixed_cost_application_method__name_override__istartswith = search_value)
                             ).distinct()

        elif 'name' in column_names:
            return qs.filter(
                            Q(tax__category__name__icontains=search_value) |
                            Q(tax_rate_percentage__tax__category__name__icontains=search_value)
                            ).distinct()

        elif 'valid_from' in column_names:
            return qs.filter(search_filters |
                             Q(valid_from__icontains=search_value)
                             ).distinct()

        elif 'valid_to' in column_names:
            if 'until further notice'.startswith(search_value.lower() or 'ufn'.startswith(search_value.lower())):
                return qs.filter(Q(valid_ufn = True))
            return qs.filter(search_filters |
                             Q(valid_to__icontains=search_value)
                             ).distinct()

        elif 'updated_at' in column_names:
            return qs.filter(search_filters |
                             Q(updated_at__icontains=search_value)
                             ).distinct()

        else:
            return qs.filter(search_filters)

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]
        if 'name' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('tax_rate_percentage__tax__category')
            else:
                qs = qs.order_by('-tax_rate_percentage__tax__category')
            return qs
        elif 'operated_as' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('applies_to_private')
            else:
                qs = qs.order_by('-applies_to_private')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
            return qs

    def customize_row(self, row, obj):

        row['specific_airport'] = obj.specific_airport.airport_details.icao_iata

        related_entries = TaxRule.objects.filter(parent_entry = obj.pk)

        if related_entries.exists() or obj.band_1_type or obj.band_2_type:
            add_class = 'has_children'
        else:
            add_class = ''

        # Airport is now the first column, so we add the 'has_children' class here where appropriate
        row['specific_airport'] = f'<span class="{add_class}">{row["specific_airport"]}</span>'

        if obj.tax:
            name = obj.tax.category.name
            row['name'] = f'<span>{name}</span>'
        else:
            name = obj.tax_rate_percentage.tax.category.name
            row['name'] = f'<span>{name}</span>'

        if obj.specific_fuel_cat:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel_cat})'
        elif obj.specific_fuel:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel})'

        if obj.specific_fee_category:
            row['applies_to_fees'] = f'Yes ({obj.specific_fee_category})'

        if obj.applies_to_commercial and obj.applies_to_private:
            row['operated_as'] = 'Commercial, Private'
        else:
            row['operated_as'] = 'Private' if obj.applies_to_private else 'Commercial'

        if obj.taxable_tax:
            taxable_tax = f'VAT: {obj.taxable_tax.get_rate_datatable_str()}'
        else:
            taxable_tax = ''

        row['rate'] = f'{obj.get_rate_datatable_str(inc_rate_type=True)}<br>{taxable_tax}'

        if add_class == 'has_children' or obj.band_1_type or obj.band_2_type:
            row['rate'] = 'Band(s) Applicable'

        row['valid_from'] = obj.valid_from

        if obj.valid_to:
            row['valid_to'] = obj.valid_to
        else:
            row['valid_to'] =  'Until Further Notice'

        row['updated_at'] = f'{obj.updated_at.strftime("%Y-%m-%d")}'

        view_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_details',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'airport'}),
                                                        button_class='fa-eye',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_view'),
                                                        button_modal=False,
                                                        modal_validation=False)


        edit_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_edit',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk,
                                                                    'type': 'airport'}),
                                                        button_class='fa-edit',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=False,
                                                        modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy('admin:tax_rule_delete',
                                                            kwargs={'country': self.kwargs['pk'], 'pk': obj.pk}),
                                                        button_class='fa-trash text-danger',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=True,
                                                        modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        return


# Various Types of Tax Subtable
class CountryTaxSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRule
    search_values_separator = '+'
    initial_order = [['band_1_start', "asc"], ['band_2_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = TaxRule.objects.filter(id=self.kwargs['pk'])
        related_entries = TaxRule.objects.filter(parent_entry = self.kwargs['pk'])

        qs = parent_entry.union(related_entries).order_by('band_1_start', 'band_2_start')

        # Not sure if it impacts performance too much, but I'm only disabling it for the subtable (to make the union work)
        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
         AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_1_start', 'title': 'Bands', 'placeholder': True, 'width': '200px'},
        {'name': 'band_2_start', 'title': 'Bands', 'placeholder': True, 'width': '200px'},
        {'name': 'rate', 'title': 'Rate', 'placeholder': True},
    ]

    def customize_row(self, row, obj):

        if obj.band_1_type:
            row['band_1_start'] = f'{obj.band_1_type}: {int(obj.band_1_start)} - {int(obj.band_1_end)}'
        if obj.band_2_type:
            row['band_2_start'] = f'{obj.band_2_type}: {int(obj.band_2_start)} - {int(obj.band_2_end)}'

        if obj.taxable_tax:
            vat_rate = f'(VAT Applicable: {obj.taxable_tax.get_rate_datatable_str()})'
        else:
            vat_rate = ''

        row['rate'] = f'{obj.get_rate_datatable_str(inc_rate_type=True, for_subtable=True)} {vat_rate}'


# Tax Rule Details
class TaxDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'official_taxes_tax_details.html'
    model = TaxRule
    context_object_name = 'entry'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['country_id'] = self.kwargs['country']
        context['tax_type'] = self.kwargs['type']
        related_entries = TaxRule.objects.filter(parent_entry = self.kwargs['pk'])\
                                         .order_by('band_1_start', 'band_2_start')
        context['related_entries'] = related_entries

        return context


# Tax Rule Delete
class TaxRuleDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'pricing_pages_includes/_modal_delete_tax_form.html'
    model = TaxRule
    form_class = ArchivalForm
    success_message = 'Tax archived successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:specific_country_tax_list',
                            kwargs={'pk': self.kwargs['country']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Archive Tax',
            'conflicting_official_taxes': [],
            'conflicting_exception_taxes': [],
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        main_entry = TaxRule.objects.filter(id = self.kwargs['pk'])
        child_entries = TaxRule.objects.filter(parent_entry = main_entry[0])
        all_entries = main_entry.union(child_entries)

        for entry in all_entries:
            related_entries = TaxRule.objects.filter(taxable_tax = entry, parent_entry = None)
            for tax_entry in related_entries:
                metacontext['conflicting_official_taxes'].append(tax_entry)

            related_exceptions = TaxRuleException.objects.filter(taxable_tax = entry, parent_entry = None, valid_ufn = True)
            for exception_entry in related_exceptions:
                metacontext['conflicting_exception_taxes'].append(exception_entry)

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':

            with transaction.atomic():

                main_entry = TaxRule.objects.filter(id = self.kwargs['pk'])
                related_entries = TaxRule.objects.filter(parent_entry = main_entry[0])
                all_entries = main_entry.union(related_entries)

                time_now = datetime.now()
                form_valid_to = form.cleaned_data.get('valid_to')

                for entry in all_entries:
                    entry.valid_ufn = False
                    entry.valid_to = form_valid_to - timedelta(days=1)
                    entry.deleted_at = time_now
                    entry.updated_by = self.request.user.person
                    entry.save()

                # Not adding deleted_at for related entries, as they are not managed like PLDs (they remain visible)
                related_official_entries = TaxRule.objects.filter(taxable_tax = main_entry[0], parent_entry = None)
                if related_official_entries.exists():
                    for entry in related_official_entries:
                        if getattr(entry, 'valid_to') is not None and entry.valid_to < form_valid_to:
                            continue
                            # If the tax is expired, we don't need to do anything with it
                        else:
                            # Get All Children
                            related_official_entries = TaxRule.objects.filter(parent_entry = entry)

                            # Store existing parent
                            existing_valid_to = copy.deepcopy(entry.valid_to)

                            if entry.valid_ufn:
                                is_ufn = True
                            else:
                                is_ufn = False

                            entry.valid_to = form_valid_to - timedelta(days=1)
                            entry.valid_ufn = False
                            # entry.deleted_at = time_now
                            entry.updated_by = self.request.user.person
                            entry.save()

                            # Create new parent
                            entry.pk = None

                            if is_ufn:
                                entry.valid_ufn = True
                                entry.valid_to = None
                            else:
                                entry.valid_ufn = False
                                entry.valid_to = existing_valid_to

                            entry.valid_from = form_valid_to
                            entry.taxable_tax = None
                            # entry.deleted_at = None
                            entry.updated_by = self.request.user.person
                            entry.save()
                            new_parent_entry = copy.deepcopy(entry)

                            for child_entry in related_official_entries:

                                # Store exinsting children
                                child_entry.valid_to = form_valid_to - timedelta(days=1)
                                child_entry.valid_ufn = False
                                # child_entry.deleted_at = time_now
                                child_entry.updated_by = self.request.user.person
                                child_entry.save()

                                # Create new children
                                child_entry.pk = None

                                if is_ufn:
                                    child_entry.valid_ufn = True
                                    child_entry.valid_to = None
                                else:
                                    child_entry.valid_ufn = False
                                    child_entry.valid_to = existing_valid_to

                                child_entry.valid_from = form_valid_to
                                child_entry.taxable_tax = None
                                # child_entry.deleted_at = None
                                child_entry.parent_entry = new_parent_entry
                                child_entry.updated_by = self.request.user.person
                                child_entry.save()

                # Only modifying the active ones, adding deleted_at for historical purposes, but we no longer manage them
                # on a PLD level
                exception_entries = TaxRuleException.objects.filter(taxable_tax = main_entry[0], valid_ufn = True, parent_entry = None)
                # Remove all in relation to the main entry (child entry is never applied separately to another tax)
                if exception_entries.exists():
                    for entry in exception_entries:

                        # Get All Children
                        # if entry.parent_entry is None:
                        related_exception_entries = TaxRuleException.objects.filter(parent_entry = entry)

                        # Store existing parent
                        entry.valid_to = form_valid_to - timedelta(days=1)
                        entry.valid_ufn = False
                        entry.deleted_at = time_now
                        entry.updated_by = self.request.user.person
                        entry.save()

                        # Create new parent
                        entry.pk = None
                        entry.valid_ufn = True
                        entry.valid_to = None
                        entry.valid_from = form_valid_to
                        entry.taxable_exception = None
                        entry.deleted_at = None
                        entry.updated_by = self.request.user.person
                        entry.save()
                        new_parent_entry = copy.deepcopy(entry)

                        for child_entry in related_exception_entries:

                            # Store exinsting children
                            child_entry.valid_to = form_valid_to - timedelta(days=1)
                            child_entry.valid_ufn = False
                            child_entry.deleted_at = time_now
                            child_entry.updated_by = self.request.user.person
                            child_entry.save()

                            # Create new children
                            child_entry.pk = None
                            child_entry.valid_ufn = True
                            child_entry.valid_to = None
                            child_entry.valid_from = form_valid_to
                            child_entry.taxable_exception = None
                            child_entry.deleted_at = None
                            child_entry.parent_entry = new_parent_entry
                            child_entry.updated_by = self.request.user.person
                            child_entry.save()

        return super().form_valid(form)

# The related js is chaotic, it needs rewriting
class TaxCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'official_taxes_tax_form.html'
    permission_required = ['pricing.p_create']

    def get(self, request, *args, **kwargs):
        country = Country.objects.get(pk=self.kwargs['pk'])

        tax_type = self.kwargs['type']
        possible_tax_types = ['country', 'airport', 'regional']
        if tax_type not in possible_tax_types:
            raise Http404(f'Tax Type "{tax_type}" does not exist!')

        if tax_type == 'country':
            tax_entries = Tax.objects.filter(applicable_country = self.kwargs['pk'])
        elif tax_type == 'regional':
            tax_entries = Tax.objects.filter(applicable_region__country = self.kwargs['pk'])
        else:
            tax_entries = Tax.objects.filter(Q(applicable_region__country = self.kwargs['pk']) |
                                             Q(applicable_country = self.kwargs['pk']))

        tax_form = TaxForm(country=country, type=tax_type)

        tax_rule_formset = NewTaxRuleFormset(form_kwargs={'country': country, 'type': tax_type},
                                             country=country, type=tax_type, prefix='tax-rule')

        tax_source_form = TaxSourceForm()

        return self.render_to_response({
            'has_tax': tax_entries.exists(),
            'tax_type': tax_type.capitalize(),
            'country': country,
            'tax_form': tax_form,
            'tax_rule_form': tax_rule_formset,
            'tax_source_form': tax_source_form
        })

    def post(self, request, *args, **kwargs):

        country = Country.objects.get(pk=self.kwargs['pk'])

        expected_forms = int(request.POST.get('tax-rule-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_1_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        tax_type = self.kwargs['type']

        if tax_type == 'country':
            tax_entries = Tax.objects.filter(applicable_country = self.kwargs['pk'])
        elif tax_type == 'regional':
            tax_entries = Tax.objects.filter(applicable_region__country = self.kwargs['pk'])
        else:
            tax_entries = Tax.objects.filter(Q(applicable_region__country = self.kwargs['pk']) |
                                         Q(applicable_country = self.kwargs['pk']))

        tax_form = TaxForm(request.POST, country=country, type=tax_type)

        tax_rule_formset = NewTaxRuleFormset(request.POST,
                                            form_kwargs={'country': country, 'type': tax_type},
                                            country=country, type=tax_type, data=request.POST,
                                            extra_fields=extra_fields, prefix='tax-rule')

        tax_source_form = TaxSourceForm(request.POST)

        if all([
            tax_form.is_valid(),
            tax_rule_formset.is_valid(),
            tax_source_form.is_valid()
        ]):
            with transaction.atomic():

                # Save Tax Entry if new
                tax_instance = tax_form.save(commit=False)
                if not tax_form.cleaned_data.get('tax_instance'):
                    tax_instance.updated_by = request.user.person
                    tax_instance.applicable_country = country
                    if self.kwargs['type'] == 'regional':
                        tax_instance.applicable_country = None
                    tax_instance.save()
                    tax_object = tax_instance
                else:
                    tax_object = Tax.objects.get(pk = tax_form.cleaned_data.get('tax_instance').pk)

                # Save Tax Rule
                for form_number, form in enumerate(tax_rule_formset):
                    tax_rule_instance = form.save(commit=False)
                    tax_rule_instance.updated_by = request.user.person

                    data = tax_rule_formset[0].cleaned_data
                    tax_rule_charging_method = data.get('tax_rule_charging_method')
                    tax_application_method = data.get('tax_unit_rate_application_method')
                    fuel_pricing_unit = data.get('fuel_pricing_unit')
                    tax_rate_percentage = data.get('tax_percentage_rate')
                    tax_rate_percentage_application_method = data.get('tax_percentage_rate_application_method')
                    taxable_tax = data.get('taxed_by_vat')
                    band_pricing = data.get(f'band_pricing_amount') # If first band has pricing
                    taxable_tax_entry = form.cleaned_data.get('taxable_tax')

                    if taxable_tax_entry:
                        child_entries = taxable_tax_entry.child_entries.all().order_by('band_1_start', 'band_2_start')
                    is_first_entry = True

                    if tax_rule_charging_method == 'Fixed':
                        tax_rule_instance.tax = tax_object

                        application_method = TaxApplicationMethod.objects.get_or_create(
                                    fixed_cost_application_method = tax_application_method)

                        tax_rule_instance.tax_application_method = application_method[0]

                    elif tax_rule_charging_method == 'Fixed-Fuel':
                        tax_rule_instance.tax = tax_object

                        application_method = TaxApplicationMethod.objects.get_or_create(
                                    fuel_pricing_unit = fuel_pricing_unit)

                        tax_rule_instance.tax_application_method = application_method[0]

                    if taxable_tax:
                        tax_rule_instance.taxable_tax = taxable_tax_entry

                    # Create and assign source
                    source_data = [tax_source_form.cleaned_data.get('name'), tax_source_form.cleaned_data.get('file_url'),
                                   tax_source_form.cleaned_data.get('web_url')]

                    if any(source_data):
                        tax_source = tax_source_form.save()
                        tax_rule_instance.tax_source = tax_source

                    current_row = 0
                    if extra_fields[0] != 0:
                        for key, value in request.POST.items():
                            if f'band_1_start' in key and value != "":
                                tax_rule_instance.band_1_start = value
                                continue
                            if f'band_1_end' in key and value != "":
                                tax_rule_instance.band_1_end = value
                                continue
                            if f'band_2_start' in key and value != "":
                                tax_rule_instance.band_2_start = value
                                continue
                            if f'band_2_end' in key and value != "":
                                tax_rule_instance.band_2_end = value
                                continue
                            if f'band_pricing' in key:

                                if tax_rule_charging_method == 'Fixed' or tax_rule_charging_method == 'Fixed-Fuel':
                                    tax_rule_instance.tax_unit_rate = value

                                elif tax_rule_charging_method == 'Percentage':
                                    if current_row == 0:
                                        tax_rate_method = data.get('band_method')
                                    else:
                                        tax_rate_method = data.get(f'band_method-additional-{form_number}-{current_row}')

                                    new_rate = TaxRatePercentage.objects.create(
                                            tax_percentage = value,
                                            tax = tax_object,
                                            tax_rate = tax_rate_method)

                                    tax_rule_instance.tax_rate_percentage = new_rate

                                if is_first_entry:
                                    tax_rule_instance.save()
                                    parent_entry = copy.deepcopy(tax_rule_instance)
                                    is_first_entry = False
                                else:
                                    tax_rule_instance.parent_entry = parent_entry
                                    # Assign taxable tax for child entries
                                    # If validation is passed, we can just assign these from top to bottom
                                    if taxable_tax:

                                        if child_entries.exists():
                                            for entry in child_entries:
                                                match = False
                                                if entry.band_1_type:
                                                    if entry.band_1_start >= tax_rule_instance.band_1_start and \
                                                    entry.band_1_end <= tax_rule_instance.band_1_end:
                                                        match = True
                                                        tax_rule_instance.taxable_tax = entry

                                                if entry.band_2_type:
                                                    if entry.band_2_start >= tax_rule_instance.band_2_start and \
                                                    entry.band_2_end <= tax_rule_instance.band_2_end:
                                                        match = True
                                                        tax_rule_instance.taxable_tax = entry

                                                if match:
                                                    break

                                    # Else just go with the main entry
                                    tax_rule_instance.save()

                                tax_rule_instance.pk = None
                                current_row += 1
                    else:

                        if band_pricing is not None and not tax_rule_charging_method == 'Percentage':
                            tax_rule_instance.tax_unit_rate = band_pricing

                        elif tax_rule_charging_method == 'Percentage':
                            if band_pricing is not None:
                                tax_rate_method = tax_rate_method = data.get('band_method')
                            else:
                                tax_rate_method = tax_rate_percentage_application_method

                            new_rate = TaxRatePercentage.objects.create(
                                tax_percentage = band_pricing if band_pricing is not None else tax_rate_percentage,
                                tax = tax_object,
                                tax_rate = tax_rate_method)

                            tax_rule_instance.tax_rate_percentage = new_rate

                        tax_rule_instance.save()

                messages.success(request, 'Tax created successfully')

                return HttpResponseRedirect(reverse_lazy('admin:specific_country_tax_list',
                                                          kwargs={'pk': country.pk}))
        else:
            return self.render_to_response({
                'has_tax': tax_entries.exists(),
                'tax_type': tax_type.capitalize(),
                'country': country,
                'tax_form': tax_form,
                'tax_rule_form': tax_rule_formset,
                'tax_source_form': tax_source_form
                })


class TaxEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'official_taxes_tax_form.html'
    permission_required = ['pricing.p_update']

    def get(self, request, *args, **kwargs):
        country = Country.objects.get(pk=self.kwargs['country'])
        tax_rule_instance = TaxRule.objects.get(id = self.kwargs['pk'])
        related_entries = TaxRule.objects.filter(parent_entry = tax_rule_instance)\
                                         .order_by('band_1_start', 'band_2_start')

        tax_type = self.kwargs['type']
        possible_tax_types = ['country', 'airport', 'regional']
        if tax_type not in possible_tax_types:
            raise Http404(f'Tax Type "{tax_type}" does not exist!')

        if tax_rule_instance.tax:
            tax_instance = tax_rule_instance.tax
        else:
            tax_instance = tax_rule_instance.tax_rate_percentage.tax

        if tax_type == 'country':
            tax_entries = Tax.objects.filter(applicable_country = country)
        elif tax_type == 'regional':
            tax_entries = Tax.objects.filter(applicable_region__country = country)
        else:
            tax_entries = Tax.objects.filter(Q(applicable_region__country = country) |
                                             Q(applicable_country = country))

        tax_form = TaxForm(country=country, tax_instance=tax_instance, type=tax_type)

        tax_rule_formset = TaxRuleFormset(form_kwargs={'country': country, 'type': tax_type},
                                          instance=tax_rule_instance, country=country, type=tax_type,
                                          related_entries=related_entries, prefix='tax-rule')

        tax_source_form = TaxSourceForm(instance=tax_rule_instance.tax_source)

        return self.render_to_response({
            'has_tax': tax_entries.exists(),
            'tax_rule': tax_rule_instance,
            'tax_type': tax_type.capitalize(),
            'country': country,
            'tax_form': tax_form,
            'tax_rule_form': tax_rule_formset,
            'tax_source_form': tax_source_form
        })

    def post(self, request, *args, **kwargs):

        expected_forms = int(request.POST.get('tax-rule-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_1_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        tax_type = self.kwargs['type']

        country = Country.objects.get(pk=self.kwargs['country'])
        parent_instance = TaxRule.objects.get(id = self.kwargs['pk'])
        tax_rule_instance = TaxRule.objects.get(id = self.kwargs['pk'])
        related_entries = TaxRule.objects.filter(parent_entry = parent_instance)\
                                         .order_by('band_1_start', 'band_2_start')

        if tax_type == 'country':
            tax_entries = Tax.objects.filter(applicable_country = self.kwargs['country'])
        elif tax_type == 'regional':
            tax_entries = Tax.objects.filter(applicable_region__country = self.kwargs['country'])
        else:
            tax_entries = Tax.objects.filter(Q(applicable_region__country = self.kwargs['country']) |
                                            Q(applicable_country = self.kwargs['country']))

        if parent_instance.tax:
            tax_instance = parent_instance.tax
        else:
            tax_instance = parent_instance.tax_rate_percentage.tax

        tax_form = TaxForm(request.POST, country=country, tax_instance=tax_instance, type=tax_type)

        tax_rule_formset = TaxRuleFormset(request.POST,
                                          form_kwargs={'country': country, 'type': tax_type},
                                          instance=tax_rule_instance, country=country, type=tax_type,
                                          extra_fields=extra_fields, data=request.POST,
                                          prefix='tax-rule')

        tax_source_form = TaxSourceForm(request.POST, instance=parent_instance.tax_source)

        if all([
            tax_form.is_valid(),
            tax_rule_formset.is_valid(),
            tax_source_form.is_valid()
        ]):
            with transaction.atomic():

                # Save Tax Entry if new
                tax_instance = tax_form.save(commit=False)
                if not tax_form.cleaned_data.get('tax_instance'):
                    tax_instance.updated_by = request.user.person
                    tax_instance.applicable_country = country
                    if self.kwargs['type'] == 'regional':
                        tax_instance.applicable_country = None
                    tax_instance.save()
                    tax_object = tax_instance
                else:
                    tax_object = Tax.objects.get(pk = tax_form.cleaned_data.get('tax_instance').pk)

                # Save Tax Rule
                new_tax_list = []
                # tax_rule_instance = tax_rule_formset.save(commit=False)
                for count, form in enumerate(tax_rule_formset):
                    tax_rule_instance = form.save(commit=False)
                    tax_rule_instance.updated_by = request.user.person

                    data = tax_rule_formset[0].cleaned_data
                    tax_rule_charging_method = data.get('tax_rule_charging_method')
                    tax_rate_percentage = data.get('tax_percentage_rate')
                    tax_rate_percentage_application_method = data.get('tax_percentage_rate_application_method')
                    taxable_tax = data.get('taxed_by_vat')
                    band_pricing = data.get('band_pricing_amount')
                    taxable_tax_entry = data.get('taxable_tax')

                    if band_pricing is not None:
                        tax_rate_method = data.get('band_method')
                    else:
                        tax_rate_method = tax_rate_percentage_application_method

                    conflicting_past_exception_taxes = data.get('past_exception_entity_id_list')
                    conflicting_past_official_taxes = data.get('past_official_entity_id_list')

                    # Duplicate current entry for historical price keeping, set new valid to date if tax is not ufn
                    if conflicting_past_exception_taxes or conflicting_past_official_taxes:

                        tax_rule_instance.valid_from = date.today()
                        if tax_rule_instance.valid_to and date.today() > tax_rule_instance.valid_to:
                            tax_rule_instance.valid_to = data.get('new_valid_to_date')

                        current_entry = TaxRule.objects.get(id = tax_rule_instance.id)
                        current_entry.valid_to = date.today() - timedelta(days=1)
                        current_entry.valid_ufn = False

                        child_entries = current_entry.child_entries.all()
                        for entry in child_entries:
                            entry.valid_to = date.today() - timedelta(days=1)
                            entry.valid_ufn = False
                            entry.save()

                        current_entry.save()

                        tax_rule_instance.pk = None

                    if taxable_tax_entry:
                        child_entries = taxable_tax_entry.child_entries.all().order_by('band_1_start', 'band_2_start')
                    existing_entry_num = 0

                    tax_application_method = data.get('tax_unit_rate_application_method')
                    if tax_application_method is None:
                        tax_application_method = data.get('fuel_pricing_unit')

                    if tax_rule_charging_method == 'Fixed':
                        tax_rule_instance.tax = tax_object

                        if band_pricing is not None:
                            tax_rule_instance.tax_unit_rate = band_pricing

                        if getattr(tax_rule_instance, 'tax_rate_percentage') is not None:
                            tax_rule_instance.tax_rate_percentage.delete()
                            tax_rule_instance.tax_rate_percentage = None

                        if getattr(tax_rule_instance, 'tax_application_method') is None:
                            tax_rule_instance.tax_application_method = TaxApplicationMethod.objects.create(
                                                                    fixed_cost_application_method = tax_application_method)
                        else:
                            tax_rule_instance.tax_application_method.fixed_cost_application_method = tax_application_method
                            tax_rule_instance.tax_application_method.fuel_pricing_unit = None
                            tax_rule_instance.tax_application_method.save()

                    elif tax_rule_charging_method == 'Fixed-Fuel':
                        tax_rule_instance.tax = tax_object

                        if band_pricing is not None:
                            tax_rule_instance.tax_unit_rate = band_pricing

                        if getattr(tax_rule_instance, 'tax_rate_percentage') is not None:
                            tax_rule_instance.tax_rate_percentage.delete()
                            tax_rule_instance.tax_rate_percentage = None

                        if getattr(tax_rule_instance, 'tax_application_method') is None:
                            tax_rule_instance.tax_application_method = TaxApplicationMethod.objects.create(
                                                                                fuel_pricing_unit = tax_application_method)
                        else:
                            tax_rule_instance.tax_application_method.fuel_pricing_unit = tax_application_method
                            tax_rule_instance.tax_application_method.fixed_cost_application_method = None
                            tax_rule_instance.tax_application_method.save()
                    else:
                        tax_percentage = tax_rate_percentage
                        tax_rule_instance.tax_unit_rate = None

                        if extra_fields == 0:
                            tax_percentage = tax_rate_percentage
                        elif band_pricing is not None:
                            tax_percentage = band_pricing

                        tax_rule_instance.tax = None

                        if getattr(tax_rule_instance, 'tax_application_method') is not None:
                            tax_rule_instance.tax_application_method.delete()
                            tax_rule_instance.tax_application_method = None

                        if getattr(tax_rule_instance, 'tax_rate_percentage') is None:
                            tax_rule_instance.tax_rate_percentage = \
                                TaxRatePercentage.objects.create(tax_percentage = tax_percentage,
                                                                 tax = tax_object,
                                                                 tax_rate = tax_rate_method)
                        else:
                            if conflicting_past_exception_taxes or conflicting_past_official_taxes:
                                new_percentage_rate = \
                                    TaxRatePercentage.objects.create(tax_percentage = tax_percentage,
                                                                     tax = tax_object,
                                                                     tax_rate = tax_rate_method)

                                tax_rule_instance.tax_rate_percentage = new_percentage_rate

                            else:
                                tax_rule_instance.tax_rate_percentage.tax_percentage = tax_percentage
                                tax_rule_instance.tax_rate_percentage.tax = tax_object
                                tax_rule_instance.tax_rate_percentage.tax_rate = tax_rate_method
                                tax_rule_instance.tax_rate_percentage.save()

                    if taxable_tax:
                        tax_rule_instance.taxable_tax = taxable_tax_entry

                    # Create and assign source
                    source_data = [tax_source_form.cleaned_data.get('name'), tax_source_form.cleaned_data.get('file_url'),
                                   tax_source_form.cleaned_data.get('web_url')]

                    if any(source_data):
                        tax_source = tax_source_form.save()
                        tax_rule_instance.tax_source = tax_source
                    else:
                        # If all fields cleared, just remove the link
                        tax_rule_instance.tax_source = None

                    if extra_fields[0] != 0:
                        tax_rule_instance.save()
                        to_list = copy.deepcopy(tax_rule_instance)
                        new_tax_list.append(to_list)
                        parent_entry = copy.deepcopy(tax_rule_instance)

                        tax_rule_instance.pk = None
                        row_number = 1

                        for key, value in request.POST.items():
                            if f'band_1_start-additional' in key and value != "":
                                tax_rule_instance.band_1_start = value
                                continue
                            if f'band_1_end-additional' in key and value != "":
                                tax_rule_instance.band_1_end = value
                                continue
                            if f'band_2_start-additional' in key and value != "":
                                tax_rule_instance.band_2_start = value
                                continue
                            if f'band_2_end-additional' in key and value != "":
                                tax_rule_instance.band_2_end = value
                                continue
                            if f'band_pricing_amount-additional' in key and value != "":

                                tax_rate_method = data.get(f'band_method-additional-{form_number}-{row_number}')

                                if tax_rule_charging_method == 'Fixed' or tax_rule_charging_method == 'Fixed-Fuel':
                                    tax_rule_instance.tax_unit_rate = value

                                if existing_entry_num < related_entries.count():
                                    tax_rule_instance.pk = related_entries[existing_entry_num].pk

                                    if tax_rule_charging_method == 'Percentage':
                                        tax_rule_instance.tax_unit_rate = None
                                        current_percentage_instance = related_entries[existing_entry_num].tax_rate_percentage
                                        if current_percentage_instance is not None and not \
                                           (conflicting_past_exception_taxes or conflicting_past_official_taxes):

                                            new_rate = \
                                                TaxRatePercentage.objects.filter(id = current_percentage_instance.pk)\
                                                                         .update(tax_percentage = value,
                                                                                 tax_rate = tax_rate_method,
                                                                                 tax = tax_object)

                                            tax_rule_instance.tax_rate_percentage = current_percentage_instance
                                        else:
                                            new_rate = TaxRatePercentage()
                                            new_rate.tax_percentage = value
                                            new_rate.tax = tax_object
                                            new_rate.tax_rate = tax_rate_method
                                            new_rate.save()

                                            tax_rule_instance.tax_rate_percentage = new_rate

                                    elif tax_rule_charging_method == 'Fixed' or tax_rule_charging_method == 'Fixed-Fuel':
                                        if related_entries[existing_entry_num].tax_rate_percentage is not None:
                                            related_entries[existing_entry_num].tax_rate_percentage.delete()

                                    existing_entry_num += 1

                                elif tax_rule_charging_method == 'Percentage':
                                    new_rate = TaxRatePercentage.objects.create(
                                                                    tax_percentage = value,
                                                                    tax = tax_object,
                                                                    tax_rate = tax_rate_method)

                                    tax_rule_instance.tax_rate_percentage = new_rate


                                tax_rule_instance.parent_entry = parent_entry
                                tax_rule_instance.updated_by = request.user.person

                                if taxable_tax:
                                    if child_entries.exists():
                                        for entry in child_entries:
                                            match = False
                                            if entry.band_1_type:
                                                if entry.band_1_start >= Decimal(tax_rule_instance.band_1_start) and \
                                                entry.band_1_end <= Decimal(tax_rule_instance.band_1_end):
                                                    match = True
                                                    tax_rule_instance.taxable_tax = entry

                                            if entry.band_2_type:
                                                if entry.band_2_start >= Decimal(tax_rule_instance.band_2_start) and \
                                                entry.band_2_end <= Decimal(tax_rule_instance.band_2_end):
                                                    match = True
                                                    tax_rule_instance.taxable_tax = entry

                                            if match:
                                                break

                                if conflicting_past_exception_taxes or conflicting_past_official_taxes:
                                    tax_rule_instance.pk = None

                                tax_rule_instance.save()
                                to_list = copy.deepcopy(tax_rule_instance)
                                new_tax_list.append(to_list)
                                tax_rule_instance.pk = None
                                row_number += 1

                    else:
                        if band_pricing is not None:
                            charging_rate = band_pricing

                            if tax_rule_charging_method == 'Percentage':
                                tax_rule_instance.tax_unit_rate = None
                            else:
                                tax_rule_instance.tax_unit_rate = charging_rate

                        else:
                            if tax_rule_charging_method == 'Percentage':
                                charging_rate = tax_rate_percentage
                                tax_rule_instance.tax_unit_rate = None

                            # else the tax_unit_rate is already associated with the instance

                                TaxRatePercentage.objects.filter(id = tax_rule_instance.tax_rate_percentage.id)\
                                                    .update(tax_percentage = charging_rate,
                                                            tax = tax_object,
                                                            tax_rate = tax_rate_method)

                        new_tax_list.append(tax_rule_instance.save())

                    while existing_entry_num < related_entries.count():
                            instance_to_delete = related_entries[existing_entry_num]
                            if instance_to_delete.tax_rate_percentage:
                                instance_to_delete.tax_rate_percentage.delete()
                            instance_to_delete.delete()
                            existing_entry_num += 1

            # Reassign active taxes and exceptions
            reassign_taxes = data.get('reassign_taxes')
            reassign_exceptions = data.get('reassign_exceptions')

            if reassign_taxes is not None:
                for entry in reassign_taxes:
                    main_entry = TaxRule.objects.filter(id = entry.id)
                    all_entries = main_entry.union(entry.child_entries.all().order_by('band_1_start', 'band_2_start'))
                    for rule_entry in all_entries:
                        match = False
                        for new_tax in new_tax_list:

                            if rule_entry.band_1_type and new_tax.band_1_type:
                                if rule_entry.band_1_start >= Decimal(new_tax.band_1_start) and \
                                   rule_entry.band_1_end <= Decimal(new_tax.band_1_end):
                                    match = True
                                    rule_entry.taxable_tax = new_tax
                                    rule_entry.save()

                            if rule_entry.band_2_type and new_tax.band_2_type:
                                if rule_entry.band_2_start >= Decimal(new_tax.band_2_start) and \
                                   rule_entry.band_2_end <= Decimal(new_tax.band_2_end):
                                    match = True
                                    rule_entry.taxable_tax = new_tax
                                    rule_entry.save()

                            if new_tax.band_1_type is None and new_tax.band_2_type is None:
                                rule_entry.taxable_tax = new_tax
                                rule_entry.save()
                                break

                            if match:
                                break


            if reassign_exceptions is not None:
                for entry in reassign_exceptions:
                    main_entry = TaxRuleException.objects.filter(id = entry.id)
                    all_entries = main_entry.union(entry.child_entries.all().order_by('band_1_start', 'band_2_start'))
                    for rule_entry in all_entries:
                        match = False
                        for new_tax in new_tax_list:

                            if rule_entry.band_1_type and new_tax.band_1_type:
                                if rule_entry.band_1_start >= Decimal(new_tax.band_1_start) and \
                                   rule_entry.band_1_end <= Decimal(new_tax.band_1_end):
                                    match = True
                                    rule_entry.taxable_tax = new_tax
                                    rule_entry.save()

                            if rule_entry.band_2_type and new_tax.band_2_type:
                                if rule_entry.band_2_start >= Decimal(new_tax.band_2_start) and \
                                   rule_entry.band_2_end <= Decimal(new_tax.band_2_end):
                                    match = True
                                    rule_entry.taxable_tax = new_tax
                                    rule_entry.save()

                            if new_tax.band_1_type is None and new_tax.band_2_type is None:
                                rule_entry.taxable_tax = new_tax
                                rule_entry.save()
                                break
                            if match:
                                break

            messages.success(request, 'Tax edited successfully')

            return HttpResponseRedirect(reverse_lazy('admin:specific_country_tax_list',
                                        kwargs={'pk': country.pk}))
        else:

            conflicting_official_taxes = tax_rule_formset[0].cleaned_data.get('official_entity_id_list')
            conflicting_exception_taxes = tax_rule_formset[0].cleaned_data.get('exception_entity_id_list')
            conflicting_past_exception_taxes = tax_rule_formset[0].cleaned_data.get('past_exception_entity_id_list')
            conflicting_past_official_taxes = tax_rule_formset[0].cleaned_data.get('past_official_entity_id_list')
            reassign_taxes = tax_rule_formset[0].cleaned_data.get('reassign_taxes')
            reassign_exceptions = tax_rule_formset[0].cleaned_data.get('reassign_exceptions')

            if any([conflicting_official_taxes, conflicting_exception_taxes, reassign_exceptions, reassign_taxes,
               conflicting_past_exception_taxes, conflicting_past_official_taxes]):
                show_modal = True
            else:
                show_modal = False

            valid_to = tax_rule_formset[0].cleaned_data.get('valid_to')

            display_date_field = False
            if valid_to and date.today() > valid_to:
                display_date_field = True

            return self.render_to_response({
                'conflicting_official_taxes': conflicting_official_taxes,
                'conflicting_exception_taxes': conflicting_exception_taxes,
                'conflicting_past_exception_taxes': conflicting_past_exception_taxes,
                'conflicting_past_official_taxes': conflicting_past_official_taxes,
                'reassign_taxes': reassign_taxes,
                'reassign_exceptions': reassign_exceptions,
                'display_date_field': display_date_field,
                'show_modal': show_modal,
                'has_tax': tax_entries.exists(),
                'tax_rule': parent_instance,
                'country': country,
                'tax_form': tax_form,
                'tax_type': tax_type.capitalize(),
                'tax_rule_form': tax_rule_formset,
                'tax_source_form': tax_source_form
                })
