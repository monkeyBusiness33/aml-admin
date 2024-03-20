import copy
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DetailView
from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from pricing.forms import NewTaxFormset, NewTaxRuleExceptionFormset, TaxFormset, TaxRuleExceptionFormset
from pricing.forms import ArchivalForm, NewTaxSourceFormset, PricingDatesSupersedeForm, TaxApplicationMethod, \
    TaxSourceFormset
from pricing.models import FuelPricingMarketPld, TaxRuleException
from pricing.utils import get_datatable_fees_action_btns
from pricing.utils.session import serialize_request_data
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin


class SupplierTaxesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRuleException
    search_values_separator = '+'
    initial_order = [['category', "asc"]]
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': TaxRuleException.objects.get(id=pk),
            'table_name': 'associated_supplier_taxes',
            'table_url': reverse_lazy('admin:associated_taxes_sublist_ajax', kwargs={
                'agreement_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        if self.source_doc_type == 'agreement':
            agreement = FuelAgreement.objects.get(pk=self.kwargs['pk'])
            qs = agreement.display_supplier_taxes
        else:
            document = FuelPricingMarketPld.objects.get(id=self.kwargs['pk'])
            qs = TaxRuleException.objects.filter(Q(parent_entry=None),
                                                 Q(exception_organisation=document.supplier),
                                                 Q(exception_airport__in=document.pld_at_location.all().values_list(
                                                     'location', flat=True)),
                                                 Q(deleted_at__isnull=True))

            if document.is_current == False:
                qs = qs.filter(valid_ufn=False)
            else:
                qs = qs.filter(valid_ufn=True)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
         'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Name', 'foreign_field': 'tax__local_name', 'placeholder': True},
        {'name': 'location', 'title': 'Location', 'placeholder': True},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'tax__category',
         'lookup_field': '__name__icontains'},
        {'name': 'applies_to_fuel', 'title': 'Fuel?'},
        {'name': 'applies_to_fees', 'title': 'Fees?'},
        {'name': 'geographic_flight_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'applicable_flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'tax_unit_rate', 'title': 'Rate', 'placeholder': True},
        {'name': 'valid_from', 'title': 'Valid From', 'lookup_field': 'valid_from__icontains'},
        {'name': 'actions', 'title': '', 'placeholder': True, 'searchable': False, 'orderable': False,
         'className': 'actions_column'},
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

            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
            if column_filter:
                search_filters |= column_filter
                if TEST_FILTERS:
                    try:
                        qstest = qs.filter(column_filter)
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name,))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'location' in column_names:
            return qs.filter(Q(Q(exception_airport__airport_details__icao_code__icontains = search_value) |
                               Q(exception_airport__airport_details__iata_code__icontains = search_value)) |
                             Q(exception_country__name__icontains = search_value))

        elif 'applies_to_fuel' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel=True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel=False))
            else:
                return qs.filter(Q(specific_fuel__name__icontains=search_value)
                                 | Q(specific_fuel_cat__name__icontains=search_value))

        elif 'applies_to_fees' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees=True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees=False))
            else:
                return qs.filter(specific_fee_category__name__icontains=search_value)

        elif 'operated_as' in column_names:
            if search_value == '0':
                return qs.filter(applies_to_commercial=True)
            elif search_value == '1':
                return qs.filter(applies_to_private=True)
            elif search_value == '2':
                return qs.filter(applies_to_commercial=True, applies_to_private=True)

        elif 'tax_unit_rate' in column_names:
            # istartswith for application methods, because they can contain numbers,
            # which can return the flat rate or percentage
            if 'band(s) applicable'.startswith(search_value.lower()) or 'bands applicable'.startswith(
                search_value.lower()):
                return qs.filter(Q(parent_entry=None), ~Q(band_1_type=None) | ~Q(band_2_type=None))
            else:
                return qs.filter(Q(tax_percentage__icontains=search_value) |
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
                return qs.filter(Q(valid_ufn=True))

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

        if 'location' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('exception_airport__airport_details__icao_code', 'exception_country__name')
            else:
                qs = qs.order_by('-exception_airport__airport_details__icao_code', '-exception_country__name')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
            return qs

    def customize_row(self, row, obj):
        related_entries = TaxRuleException.objects.filter(parent_entry=obj.pk)

        if related_entries.exists() or obj.band_1_type or obj.band_2_type:
            add_class = 'has_children'
        else:
            add_class = ''

        if obj.specific_fuel_cat:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel_cat})'
        elif obj.specific_fuel:
            row['applies_to_fuel'] = f'Yes ({obj.specific_fuel})'

        if obj.specific_fee_category:
            row['applies_to_fees'] = f'Yes ({obj.specific_fee_category})'

        row['name'] = f'<span class="{add_class}"\>{obj.tax.local_name}</span>'

        if obj.exception_airport:
            row['location'] = obj.exception_airport.airport_details.icao_iata
        else:
            row['location'] = obj.exception_country.name

        formatted_flight_type = (obj.applicable_flight_type.name).split('Only')[0].strip()

        if formatted_flight_type[-1] != 's':
            formatted_flight_type += 's'

        row['applicable_flight_type'] = formatted_flight_type

        if obj.taxable_tax:
            vat_rate = f'<br> (VAT Applicable: {obj.taxable_tax.get_rate_datatable_str()})'
        else:
            vat_rate = ''

        if obj.taxable_exception:
            exception_rate = f'<br> (Exception Applicable: {obj.taxable_exception.get_rate_datatable_str()})'
        else:
            exception_rate = ''

        row['tax_unit_rate'] = f'{obj.get_rate_datatable_str()} {vat_rate} {exception_rate}'

        if obj.band_1_type or obj.band_2_type:
            row['tax_unit_rate'] = 'Band(s) Apply'

        row['valid_from'] = obj.valid_from
        row['updated_at'] = f'{obj.updated_at.strftime("%Y-%m-%d")}'

        if self.source_doc_type == 'agreement':
            view_url = reverse_lazy(
                'admin:agreement_supplier_tax_details',
                kwargs={'pk': obj.pk, 'agreement_pk': self.kwargs['pk']})
            edit_url = reverse_lazy(
                'admin:agreement_supplier_tax_edit',
                kwargs={'pk': obj.pk, 'agreement_pk': self.kwargs['pk']})
            archive_url = reverse_lazy(
                'admin:agreement_supplier_tax_archive',
                kwargs={'pk': obj.pk})
        else:
            view_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_supplier_defined_tax_details',
                kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']})
            edit_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_supplier_defined_tax_edit',
                kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']})
            archive_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_supplier_defined_tax_archive',
                kwargs={'pk': obj.pk})

        row['actions'] = get_datatable_fees_action_btns({
            'view_url': view_url,
            'view_perm': 'pricing.p_view',
            'edit_url': edit_url,
            'edit_perm': 'pricing.p_update',
            'archive_url': archive_url,
            'archive_perm': 'pricing.p_udpate',
        }, self.request)

        return


class SupplierTaxesSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRuleException
    search_values_separator = '+'
    initial_order = [['band_1_start', "asc"]]
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

    def get_initial_queryset(self, request=None):
        parent_entry = TaxRuleException.objects.filter(id=self.kwargs['pk'])
        related_entries = TaxRuleException.objects.filter(parent_entry=self.kwargs['pk'])
        qs = parent_entry.union(related_entries).order_by('band_1_start', 'band_2_start')

        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_1_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'band_2_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'tax_unit_rate', 'title': 'Rate', 'placeholder': True},
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True, },
    ]

    def customize_row(self, row, obj):
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        if obj.band_1_type:
            row['band_1_start'] = f'{obj.band_1_type}: {int(obj.band_1_start)} - {int(obj.band_1_end)}'
        if obj.band_2_type:
            row['band_2_start'] = f'{obj.band_2_type}: {int(obj.band_2_start)} - {int(obj.band_2_end)}'

        if obj.taxable_tax:
            vat_rate = f'(VAT Applicable: {obj.taxable_tax.get_rate_datatable_str()})'
        else:
            vat_rate = ''

        if obj.taxable_exception:
            exception_rate = f'(Exception Applicable: {obj.taxable_exception.get_rate_datatable_str()})'
        else:
            exception_rate = ''

        row['tax_unit_rate'] = f'{obj.get_rate_datatable_str()} {vat_rate} {exception_rate}'

        return


class SupplierTaxDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'supplier_tax_details.html'
    model = TaxRuleException
    context_object_name = 'entry'
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'agreement_pk' in self.kwargs else 'pld'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = TaxRuleException.objects.get(id=self.kwargs['pk'])
        related_entries = TaxRuleException.objects.filter(parent_entry=instance) \
            .order_by('band_1_start', 'band_2_start')

        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(id=self.kwargs['agreement_pk'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement',
                                         kwargs={'pk': document.id}),
                'source_doc_url': reverse_lazy('admin:fuel_agreement',
                                               kwargs={'pk': document.id}),
                'edit_url': reverse_lazy('admin:agreement_supplier_tax_edit',
                                         kwargs={'pk': self.object.pk, 'agreement_pk': document.pk}),
                'archive_url': reverse_lazy('admin:agreement_supplier_tax_archive',
                                            kwargs={'pk': self.object.pk}),
            }
        else:
            document = FuelPricingMarketPld.objects.get(id=self.kwargs['pld'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details',
                                         kwargs={'pk': document.id}),
                'source_doc_url': reverse_lazy('admin:fuel_pricing_market_document_details',
                                               kwargs={'pk': document.id}),
                'edit_url': reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_edit',
                                         kwargs={'pk': self.object.pk, 'pld': document.id}),
                'archive_url': reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_archive',
                                            kwargs={'pk': self.object.pk}),
            }

        context['document_type'] = self.source_doc_type
        context['document'] = document
        context['related_entries'] = related_entries
        context['metacontext'] = metacontext

        return context


class SupplierTaxesCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_taxes_create.html'
    permission_required = ['pricing.p_create']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'agreement_pk' in self.kwargs else 'pld'

    def get(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pk'])

        new_tax_formset = NewTaxFormset(document=document, doc_type=self.source_doc_type, prefix='tax')

        new_tax_rule_exception_formset = NewTaxRuleExceptionFormset(
            form_kwargs={'document': document, 'doc_type': self.source_doc_type, 'context': 'Create'},
            document=document, doc_type=self.source_doc_type, context='Create', prefix='new-tax-rule-exception',
            tax_formset=new_tax_formset)

        new_tax_source_formset = NewTaxSourceFormset(prefix='new-tax-source')

        if self.source_doc_type == 'agreement':
            locations = document.all_pricing_location_pks
            countries = [p.location.details.country for p in document.all_pricing]
            fuel_tax_entries = TaxRuleException.objects.filter(Q(exception_organisation=document.supplier),
                                                               Q(source_agreement=document),
                                                               Q(deleted_at__isnull=True),
                                                               Q(valid_ufn=True),
                                                               Q(Q(exception_airport__in=locations) |
                                                                 Q(exception_country__in=countries)))
        else:
            locations = document.pld_at_location.all().values_list('location', flat=True)
            countries = document.pld_at_location.all().values('location__details__country')
            fuel_tax_entries = TaxRuleException.objects.filter(Q(exception_organisation=document.supplier),
                                                               Q(related_pld=document),
                                                               Q(deleted_at__isnull=True),
                                                               Q(valid_ufn=True),
                                                               Q(Q(exception_airport__in=locations) |
                                                                 Q(exception_country__in=countries)))

        new_doc = False
        if request.session.get(f'{self.source_doc_type}-{document.id}') and not fuel_tax_entries.exists():
            new_doc = True

        return self.render_to_response({
            'context': 'Create',
            'doc_is_new': new_doc,
            'doc_instance': document,
            'tax_formset': new_tax_formset,
            'tax_rule_exception_formset': new_tax_rule_exception_formset,
            'tax_source_formset': new_tax_source_formset,
        })

    def post(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
            redirect_url = reverse_lazy('admin:fuel_agreement', kwargs={'pk': document.id})
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pk'])
            redirect_url = reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': document.id})

        if 'skip' in request.POST['button-pressed']:
            request.session.pop(f'{self.source_doc_type}-{document.id}', None)
            return HttpResponseRedirect(redirect_url)

        expected_forms = int(request.POST.get('new-tax-rule-exception-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_1_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        new_tax_formset = NewTaxFormset(request.POST, document=document, doc_type=self.source_doc_type, prefix='tax')

        new_tax_rule_exception_formset = NewTaxRuleExceptionFormset(
            request.POST,
            form_kwargs={'document': document, 'doc_type': self.source_doc_type, 'context': 'Create'},
            document=document, doc_type=self.source_doc_type, context='Create', extra_fields=extra_fields,
            prefix='new-tax-rule-exception', tax_formset=new_tax_formset)

        new_tax_source_formset = NewTaxSourceFormset(request.POST, prefix='new-tax-source')

        if all([
            new_tax_formset.is_valid(),
            new_tax_rule_exception_formset.is_valid(),
            new_tax_source_formset.is_valid()
        ]):
            with transaction.atomic():

                for form_number, form in enumerate(new_tax_rule_exception_formset):
                    if form.has_changed() and not form.cleaned_data.get('DELETE'):
                        exception = form.save(commit=False)
                        exception.exception_organisation = document.supplier
                        exception.updated_by = self.request.user.person
                        exception.valid_ufn = True

                        if self.source_doc_type == 'agreement':
                            exception.source_agreement = document
                        else:
                            exception.related_pld = document

                        band_pricing = form.cleaned_data.get('band_pricing_amount')
                        charging_method = form.cleaned_data.get('charging_method')
                        application_method = form.cleaned_data.get('application_method')
                        fuel_application_method = form.cleaned_data.get('fuel_pricing_unit')

                        if application_method:
                            exception.tax_application_method = TaxApplicationMethod.objects.get_or_create(
                                fixed_cost_application_method=application_method)[0]
                            exception.tax_percentage = None
                            if band_pricing is not None:
                                exception.tax_unit_rate = band_pricing
                        elif fuel_application_method:
                            exception.tax_application_method = TaxApplicationMethod.objects.get_or_create(
                                fuel_pricing_unit=fuel_application_method)[0]
                            exception.tax_percentage = None
                            if band_pricing is not None:
                                exception.tax_unit_rate = band_pricing

                        else:
                            exception.tax_unit_rate = None
                            if band_pricing is not None:
                                exception.tax_percentage = band_pricing

                        tax_form = new_tax_formset[form_number]
                        if tax_form.cleaned_data.get('tax_instance'):
                            exception.tax = tax_form.cleaned_data.get('tax_instance')
                        else:
                            new_tax = tax_form.save(commit=False)

                            if form.cleaned_data.get('exception_country') is not None:
                                new_tax.applicable_country = exception.exception_country
                            else:
                                new_tax.applicable_country = exception.exception_airport.details.country

                            new_tax.updated_by = self.request.user.person
                            exception.tax = tax_form.save()

                        source_form = new_tax_source_formset[form_number]
                        if source_form.has_changed():
                            exception.tax_source = source_form.save()

                        exception.save()

                        parent_entry = copy.deepcopy(exception)
                        exception.pk = None

                        if extra_fields[form_number] != 0:
                            row_number = 0
                            for key, value in request.POST.items():
                                if f'-{form_number}-band_1_start-additional' in key and value != "":
                                    exception.band_1_start = value
                                    continue
                                if f'-{form_number}-band_1_end-additional' in key and value != "":
                                    exception.band_1_end = value
                                    continue
                                if f'-{form_number}-band_2_start-additional' in key and value != "":
                                    exception.band_2_start = value
                                    continue
                                if f'-{form_number}-band_2_end-additional' in key and value != "":
                                    exception.band_2_end = value
                                    continue
                                if f'-{form_number}-band_pricing_amount-additional' in key:

                                    if charging_method == 'Percentage':
                                        exception.tax_percentage = value
                                    else:
                                        exception.tax_unit_rate = value

                                    exception.parent_entry = parent_entry

                                    if exception.taxable_tax is not None:
                                        child_entries = exception.taxable_tax.child_entries.all().order_by(
                                            'band_1_start', 'band_2_start')
                                        if child_entries.exists():
                                            exception.taxable_tax = child_entries[row_number]
                                        # Else just go with the main entry
                                    if exception.taxable_exception is not None:
                                        child_entries = exception.taxable_exception.child_entries.all().order_by(
                                            'band_1_start', 'band_2_start')
                                        if child_entries.exists():
                                            exception.taxable_exception = child_entries[row_number]

                                    exception.save()
                                    exception.pk = None
                                    row_number += 1

                messages.success(request, 'Supplier-Defined Tax saved successfully')

                if request.session.get(f'{self.source_doc_type}-{document.id}-supplier_tax_data'):
                    del request.session[f'{self.source_doc_type}-{document.id}-supplier_tax_data']
                    if self.source_doc_type == 'agreement':
                        return HttpResponseRedirect(
                            reverse_lazy('admin:agreement_supplier_tax_supersede',
                                         kwargs={'pk': document.superseded_by.pk}))
                    else:
                        return HttpResponseRedirect(
                            reverse_lazy('admin:fuel_pricing_market_documents_supersede_supplier_taxes',
                                         kwargs={'pk': document.pk}))
                else:
                    request.session.pop(f'{self.source_doc_type}-{document.id}', None)
                    if self.source_doc_type == 'agreement':
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                                 kwargs={'pk': document.id}))
                    else:
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                                 kwargs={'pk': document.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            if self.source_doc_type == 'agreement':
                locations = document.all_pricing_location_pks
                countries = [p.location.details.country for p in document.all_pricing]
                fuel_tax_entries = TaxRuleException.objects.filter(Q(exception_organisation=document.supplier),
                                                                   Q(source_agreement=document),
                                                                   Q(deleted_at__isnull=True),
                                                                   Q(valid_ufn=True),
                                                                   Q(Q(exception_airport__in=locations) |
                                                                     Q(exception_country__in=countries)))
            else:
                locations = document.pld_at_location.all().values_list('location', flat=True)
                countries = document.pld_at_location.all().values('location__details__country')
                fuel_tax_entries = TaxRuleException.objects.filter(Q(exception_organisation=document.supplier),
                                                                   Q(related_pld=document),
                                                                   Q(deleted_at__isnull=True),
                                                                   Q(valid_ufn=True),
                                                                   Q(Q(exception_airport__in=locations) |
                                                                     Q(exception_country__in=countries)))

            new_doc = False
            if request.session.get(f'{self.source_doc_type}-{document.id}') and not fuel_tax_entries.exists():
                new_doc = True

            return self.render_to_response({
                'context': 'Create',
                'doc_is_new': new_doc,
                'doc_instance': document,
                'tax_formset': new_tax_formset,
                'tax_rule_exception_formset': new_tax_rule_exception_formset,
                'tax_source_formset': new_tax_source_formset,
            })


class SupplierTaxEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_tax_edit.html'
    permission_required = ['pricing.p_update']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'agreement_pk' in self.kwargs else 'pld'

    def get(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement', kwargs={'pk': document.id})
            }
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': document.id})
            }

        entry = TaxRuleException.objects.get(id=self.kwargs['pk'], deleted_at__isnull=True)
        related_entries = TaxRuleException.objects.filter(parent_entry=entry).order_by('band_1_start', 'band_2_start')

        tax_formset = TaxFormset(instance=entry, document=document, doc_type=self.source_doc_type, prefix='tax')

        tax_rule_exception_formset = TaxRuleExceptionFormset(
            form_kwargs={'document': document, 'doc_type': self.source_doc_type, 'instance': entry, 'context': 'Edit'},
            document=document, doc_type=self.source_doc_type, instance=entry, related_entries=related_entries,
            context='Edit', prefix='new-tax-rule-exception', tax_formset=tax_formset)

        tax_source_formset = TaxSourceFormset(instance=entry, prefix='tax-source')

        return self.render_to_response({
            'pld_instance': document,
            'tax_formset': tax_formset,
            'tax_rule_exception_formset': tax_rule_exception_formset,
            'tax_source_formset': tax_source_formset,
            'metacontext': metacontext,
        })

    def post(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement', kwargs={'pk': document.id})
            }
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': document.id})
            }

        entry = TaxRuleException.objects.get(id=self.kwargs['pk'], deleted_at__isnull=True)
        related_entries = TaxRuleException.objects.filter(parent_entry=entry).order_by('band_1_start', 'band_2_start')

        expected_forms = int(request.POST.get('new-tax-rule-exception-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_1_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        tax_formset = TaxFormset(request.POST, instance=entry,
                                 document=document, doc_type=self.source_doc_type, prefix='tax')

        tax_rule_exception_formset = TaxRuleExceptionFormset(
            request.POST,
            form_kwargs={'document': document, 'doc_type': self.source_doc_type, 'instance': entry, 'context': 'Edit'},
            document=document, doc_type=self.source_doc_type, instance=entry, related_entries=related_entries,
            extra_fields=extra_fields,
            context='Edit', prefix='new-tax-rule-exception', tax_formset=tax_formset)

        tax_source_formset = TaxSourceFormset(request.POST, prefix='tax-source')

        if all([
            tax_formset.is_valid(),
            tax_rule_exception_formset.is_valid(),
            tax_source_formset.is_valid()
        ]):
            with transaction.atomic():

                for form_number, form in enumerate(tax_rule_exception_formset):
                    if form.has_changed() or tax_source_formset[form_number].has_changed():
                        exception = form.save(commit=False)
                        exception.exception_organisation = document.supplier
                        exception.updated_by = self.request.user.person
                        exception.valid_ufn = True

                        if self.source_doc_type == 'agreement':
                            exception.source_agreement = document
                        else:
                            exception.related_pld = document

                        band_pricing = form.cleaned_data.get('band_pricing_amount')
                        charging_method = form.cleaned_data.get('charging_method')
                        application_method = form.cleaned_data.get('application_method')
                        fuel_application_method = form.cleaned_data.get('fuel_pricing_unit')

                        if application_method:
                            exception.tax_application_method = TaxApplicationMethod.objects.get_or_create(
                                fixed_cost_application_method=application_method)[0]
                            if band_pricing is not None:
                                exception.tax_unit_rate = band_pricing
                        elif fuel_application_method:
                            exception.tax_application_method = TaxApplicationMethod.objects.get_or_create(
                                fuel_pricing_unit=fuel_application_method)[0]

                            if band_pricing is not None:
                                exception.tax_unit_rate = band_pricing

                        elif band_pricing is not None:
                            exception.tax_percentage = band_pricing

                        if not application_method and not fuel_application_method:
                            exception.tax_application_method = None

                        tax_form = tax_formset[form_number]
                        if tax_form.cleaned_data.get('tax_instance'):
                            exception.tax = tax_form.cleaned_data.get('tax_instance')
                        else:
                            new_tax = tax_form.save(commit=False)

                            if form.cleaned_data.get('exception_country') is not None:
                                new_tax.applicable_country = exception.exception_country
                            else:
                                new_tax.applicable_country = exception.exception_airport.details.country

                            new_tax.updated_by = self.request.user.person
                            exception.tax = tax_form.save()

                        source_form = tax_source_formset[form_number]
                        source_instance = tax_source_formset[form_number].save(commit=False)

                        source_data = [source_form.cleaned_data.get('name'), source_form.cleaned_data.get('file_url'),
                                       source_form.cleaned_data.get('web_url')]
                        if any(source_data):
                            if exception.tax_source:
                                source_instance.id = exception.tax_source_id

                            source_instance.save()
                            exception.tax_source = source_instance
                        else:
                            # If all fields cleared, just remove the link
                            exception.tax_source = None

                        exception.save()

                        parent_entry = copy.deepcopy(exception)
                        exception.pk = None
                        existing_entry = 0
                        exception.parent_entry = parent_entry

                        if extra_fields[form_number] != 0:
                            row_number = 0
                            for key, value in request.POST.items():
                                if f'-{form_number}-band_1_start-additional' in key and value != "":
                                    exception.band_1_start = value
                                    continue
                                if f'-{form_number}-band_1_end-additional' in key and value != "":
                                    exception.band_1_end = value
                                    continue
                                if f'-{form_number}-band_2_start-additional' in key and value != "":
                                    exception.band_2_start = value
                                    continue
                                if f'-{form_number}-band_2_end-additional' in key and value != "":
                                    exception.band_2_end = value
                                    continue
                                if f'-{form_number}-band_pricing_amount-additional' in key:

                                    if charging_method == 'Percentage':
                                        exception.tax_percentage = value
                                    else:
                                        exception.tax_unit_rate = value

                                    if exception.taxable_tax is not None:
                                        child_entries = exception.taxable_tax.child_entries.all().order_by(
                                            'band_1_start', 'band_2_start')
                                        if child_entries.exists():
                                            exception.taxable_tax = child_entries[row_number]
                                        # Else just go with the main entry
                                    if exception.taxable_exception is not None:
                                        child_entries = exception.taxable_exception.child_entries.all().order_by(
                                            'band_1_start', 'band_2_start')
                                        if child_entries.exists():
                                            exception.taxable_exception = child_entries[row_number]

                                    if existing_entry < related_entries.count():
                                        exception.pk = related_entries[existing_entry].pk
                                        exception.save()
                                        existing_entry += 1
                                    else:
                                        exception.save()

                                    exception.pk = None
                                    row_number += 1

                        while existing_entry < related_entries.count():
                            instance_to_delete = related_entries[existing_entry]
                            instance_to_delete.delete()
                            existing_entry += 1

                messages.success(request, 'Supplier-Defined Tax saved successfully')

                if request.session.get(f'{self.source_doc_type}-{document.id}-supplier_tax_data'):
                    if self.source_doc_type == 'agreement':
                        return HttpResponseRedirect(
                            reverse_lazy('admin:agreement_supplier_tax_supersede',
                                         kwargs={'pk': document.id}))
                    else:
                        return HttpResponseRedirect(
                            reverse_lazy('admin:fuel_pricing_market_documents_supersede_supplier_taxes',
                                         kwargs={'pk': document.id}))
                else:
                    request.session.pop(f'pld-{document.id}', None)
                    if self.source_doc_type == 'agreement':
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                                 kwargs={'pk': document.id}))
                    else:
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                                 kwargs={'pk': document.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            conflicting_exception_ids = tax_rule_exception_formset[0].cleaned_data.get('exception_entity_id_list')

            if conflicting_exception_ids:
                show_modal = True
            else:
                show_modal = False

            return self.render_to_response({
                'show_modal': show_modal,
                'conflicting_exception_taxes': conflicting_exception_ids,
                'doc_instance': document,
                'tax_formset': tax_formset,
                'tax_rule_exception_formset': tax_rule_exception_formset,
                'tax_source_formset': tax_source_formset,
                'metacontext': metacontext,
            })


class SupplierTaxArchiveView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'pricing_pages_includes/_modal_delete_tax_form.html'
    model = TaxRuleException
    form_class = ArchivalForm
    success_message = 'Tax archived successfully'
    permission_required = ['pricing.p_update']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Archive Tax',
            'conflicting_exception_taxes': [],
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        main_entry = TaxRuleException.objects.filter(id=self.kwargs['pk'])
        child_entries = TaxRuleException.objects.filter(parent_entry=main_entry[0])
        all_entries = main_entry.union(child_entries)

        for entry in all_entries:
            related_exceptions = TaxRuleException.objects.filter(taxable_exception=entry, parent_entry=None)
            for entry in related_exceptions:
                metacontext['conflicting_exception_taxes'].append(entry)

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            with transaction.atomic():
                main_entry = TaxRuleException.objects.filter(id=self.kwargs['pk'])
                related_entries = TaxRuleException.objects.filter(parent_entry=main_entry[0])
                all_entries = main_entry.union(related_entries)

                time_now = datetime.now()
                form_valid_to = form.cleaned_data.get('valid_to')

                for entry in all_entries:
                    entry.valid_ufn = False
                    entry.deleted_at = time_now
                    entry.valid_to = form_valid_to - timedelta(days=1)
                    entry.updated_by = self.request.user.person
                    entry.save()

                # Remove taxable tax relation for active entries
                exception_entries = TaxRuleException.objects.filter(taxable_exception=main_entry[0], valid_ufn=True,
                                                                    parent_entry=None, deleted_at__isnull=False)

                # Remove all in relation to the main entry (child entry is never applied separately to another tax)
                # Not duplicating here as they are essentially actively managed, if current, but historical pricing is
                # of importance, then users can adjust by editing/creating
                if exception_entries.exists():
                    for entry in exception_entries:
                        entry.taxable_exception = None
                        for child_entry in entry.child_entries.all():
                            child_entry.taxable_exception = None
                            child_entry.save()
                        entry.save()

        return super().form_valid(form)


class SupplierTaxesSupersedeView(AdminPermissionsMixin, TemplateView):
    template_name = 'supplier_taxes_supersede.html'
    permission_required = ['pricing.p_create']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

        if self.source_doc_type == 'agreement':
            self.new_document = FuelAgreement.objects.get(pk=self.kwargs.get('pk', None))
            self.old_document = self.new_document.superseded_agreement
            self.session_doc_pk = self.new_document.pk
            self.return_url = reverse_lazy('admin:agreement_pricing_supersede',
                                           kwargs={'pk': self.new_document.id})
            self.supersede_pricing_url = reverse_lazy('admin:agreement_pricing_supersede',
                                                      kwargs={'pk': self.new_document.id})
            self.supersede_fees_url = reverse_lazy('admin:agreement_supplier_fees_supersede',
                                                   kwargs={'pk': self.new_document.id})
            self.create_taxes_url = reverse_lazy('admin:agreement_supplier_tax_create',
                                                 kwargs={'agreement_pk': self.old_document.id})
        else:
            self.new_document = None
            self.old_document = FuelPricingMarketPld.objects.get(pk=self.kwargs.get('pk', None))
            self.session_doc_pk = self.old_document.pk
            self.return_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_pricing',
                                           kwargs={'pk': self.old_document.id})
            self.supersede_pricing_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_pricing',
                                                      kwargs={'pk': self.old_document.id})
            self.supersede_fees_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_associated_fees',
                                                   kwargs={'pk': self.old_document.id})
            self.create_taxes_url = reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_create_page',
                                                 kwargs={'pk': self.old_document.id})

    def get(self, request, *args, **kwargs):
        old_document = self.old_document
        new_document = self.new_document

        tax_rule_exception_formset = TaxRuleExceptionFormset(
            form_kwargs={'document': old_document, 'new_document': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            document=old_document, new_document=new_document, doc_type=self.source_doc_type,
            context='Supersede', prefix='tax-rule-exception')

        update_date_form = PricingDatesSupersedeForm(prefix='update-date')

        # For debugging purposes
        # del request.session[f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data']

        if f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data' in request.session:
            session_data = request.session[f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data']

            expected_forms = int(session_data.get('tax-rule-exception-TOTAL_FORMS'))
            extra_fields = {i: 0 for i in range(expected_forms)}

            for form_number in extra_fields:
                for key in session_data:
                    if f'band_1_start-additional-{form_number}-' in key:
                        extra_fields[form_number] += 1

            tax_rule_exception_formset = TaxRuleExceptionFormset(
                session_data,
                form_kwargs={'document': old_document, 'new_document': new_document,
                             'doc_type': self.source_doc_type, 'context': 'Supersede'},
                document=old_document, new_document=new_document, doc_type=self.source_doc_type,
                context='Supersede', extra_fields=extra_fields, prefix='tax-rule-exception')

            update_date_form = PricingDatesSupersedeForm(session_data,
                                                         prefix='update-date')

        return self.render_to_response({
            'associated_fee_saved': request.session.get(f'{self.source_doc_type}-{self.session_doc_pk}-associated-fee-saved', None),
            'document': old_document,
            'new_document': new_document,
            'document_type': self.source_doc_type,
            'tax_rule_exception_formset': tax_rule_exception_formset,
            'update_date_form': update_date_form
        })

    def post(self, request, *args, **kwargs):
        old_document = self.old_document
        new_document = self.new_document

        form_numbers = request.POST.get('tax-rule-exception-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        for form_number in extra_fields:
            for key in request.POST:
                if f'-{form_number}-band_1_start-additional' in key:
                    extra_fields[form_number] += 1

        tax_rule_exception_formset = TaxRuleExceptionFormset(
            request.POST,
            form_kwargs={'document': old_document, 'new_document': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            document=old_document, new_document=new_document, doc_type=self.source_doc_type,
            context='Supersede', extra_fields=extra_fields, prefix='tax-rule-exception')

        update_date_form = PricingDatesSupersedeForm(request.POST,
                                                     context='fuel_fee',
                                                     prefix='update-date')

        if request.POST['button-pressed'] != 'save':
            request.session[f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data'] = serialize_request_data(request.POST)
            request.session[self.source_doc_type] = self.session_doc_pk

            if 'fuel-pricing' in request.POST['button-pressed']:
                messages.info(request, 'Supplier-Defined Tax form fields were saved')
                return HttpResponseRedirect(self.supersede_pricing_url)

            elif 'associated-fees' in request.POST['button-pressed']:
                messages.info(request, 'Supplier-Defined Tax form fields were saved')
                return HttpResponseRedirect(self.supersede_fees_url)

            elif 'supplier-tax-create' in request.POST['button-pressed']:
                messages.warning(request,
                                 'Supplier-Defined Tax form fields\' state will be deleted after new tax creation!')
                return HttpResponseRedirect(self.create_taxes_url)

        if all([
            tax_rule_exception_formset.is_valid(),
            update_date_form.is_valid()
        ]):
            with transaction.atomic():

                formset = tax_rule_exception_formset.save(commit=False)
                time_now = datetime.now()

                # Init for taxable exception shift checking
                exceptions_main_tax = {}

                if self.source_doc_type == 'agreement':
                    tax_entries = TaxRuleException.objects.filter(deleted_at__isnull=True, valid_ufn=True,
                                                                  source_agreement=old_document)
                else:
                    tax_entries = TaxRuleException.objects.filter(deleted_at__isnull=True, valid_ufn=True,
                                                                  related_pld=old_document)

                for entry in tax_entries:
                    exceptions_main_tax[entry] = None

                for form_number, form in enumerate(tax_rule_exception_formset):
                    instance = form.save(commit=False)
                    no_change = request.POST.get(f'tax-rule-exception-{form_number}-no_change')
                    charging_method = request.POST.get(f'tax-rule-exception-{form_number}-charging_method')
                    flat_application_method = request.POST.get(f'tax-rule-exception-{form_number}-application_method')
                    fuel_application_method = request.POST.get(f'tax-rule-exception-{form_number}-fuel_pricing_unit')
                    rate_amount = request.POST.get(f'tax-rule-exception-{form_number}-band_pricing_amount')
                    valid_to_date = request.POST.get(f'tax-rule-exception-{form_number}-valid_to')

                    if update_date_form.cleaned_data.get('valid_from'):
                        valid_from = update_date_form.cleaned_data.get('valid_from')
                    else:
                        valid_from = instance.valid_from

                    if instance in tax_rule_exception_formset.deleted_objects:
                        TaxRuleException.objects.filter(id=instance.id) \
                            .update(valid_to=valid_to_date,
                                    valid_ufn=False,
                                    deleted_at=time_now,
                                    updated_by=request.user.person)
                        continue

                    # Always store current entries
                    parent_entry = TaxRuleException.objects.filter(id=instance.id)
                    related_entries = TaxRuleException.objects.filter(parent_entry=instance)
                    all_entries = parent_entry.union(related_entries)

                    for entry in all_entries:
                        entry.updated_by = request.user.person
                        entry.valid_ufn = False
                        if no_change == 'on':
                            entry.valid_to = time_now - timedelta(days=1)
                        else:
                            entry.valid_to = valid_from - timedelta(days=1)
                        entry.save()

                    # When 'no_change' is checked, we duplicate the entries and cut back the validity to today
                    # (preserve taxable tax structures)
                    if no_change == 'on':
                        exception_cleared = False
                        official_cleared = False

                        current_instance = copy.deepcopy(instance)
                        instance.pk = None
                        instance.valid_ufn = True
                        instance.valid_to = None
                        instance.valid_from = time_now

                        if charging_method == 'Percentage':
                            instance.tax_percentage = rate_amount
                            instance.tax_unit_rate = None
                            instance.tax_application_method = None
                        else:
                            instance.tax_percentage = None
                            instance.tax_unit_rate = rate_amount

                        if form.cleaned_data.get(f'form-{form_number}-exception_entity_list') or \
                            form.cleaned_data.get(f'form-{form_number}-exception_mismatch'):
                            exception_cleared = True
                            instance.taxable_exception = None

                        if form.cleaned_data.get(f'form-{form_number}-official_mismatch'):
                            official_cleared = True
                            instance.taxable_tax = None

                        instance.save()

                        if exceptions_main_tax.get(current_instance) is None and not exception_cleared:
                            exceptions_main_tax.update({current_instance: instance})

                        new_parent_entry = copy.deepcopy(instance)
                        for entry in related_entries:
                            current_entry = copy.deepcopy(entry)
                            entry.pk = None
                            entry.valid_ufn = True
                            entry.valid_to = None
                            entry.valid_from = time_now
                            entry.parent_entry = new_parent_entry

                            if official_cleared:
                                entry.taxable_tax = None
                            if exception_cleared:
                                entry.taxable_exception = None

                            entry.save()
                            if exceptions_main_tax.get(current_entry) is None and not exception_cleared:
                                exceptions_main_tax.update({current_entry: instance})

                    else:
                        # Save new main entry
                        if charging_method == 'Percentage':
                            instance.tax_percentage = rate_amount
                            instance.tax_unit_rate = None
                            instance.tax_application_method = None
                        else:
                            instance.tax_percentage = None
                            instance.tax_unit_rate = rate_amount

                            if flat_application_method:
                                instance.tax_application_method = \
                                    TaxApplicationMethod.objects.get_or_create(
                                        fixed_cost_application_method=flat_application_method)[0]
                            elif fuel_application_method:
                                instance.tax_application_method = \
                                    TaxApplicationMethod.objects.get_or_create(
                                        fuel_pricing_unit=fuel_application_method)[0]

                        existing_parent_entry = TaxRuleException.objects.get(id=instance.id)

                        exception_cleared = False

                        if form.cleaned_data.get(f'form-{form_number}-exception_entity_list') or \
                            form.cleaned_data.get(f'form-{form_number}-exception_mismatch'):
                            exception_cleared = True
                            instance.taxable_exception = None

                        if form.cleaned_data.get(f'form-{form_number}-official_mismatch'):
                            instance.taxable_tax = None
                        else:
                            instance.taxable_tax = existing_parent_entry.taxable_tax

                        instance.valid_from = valid_from
                        instance.valid_ufn = True
                        instance.valid_to = None
                        current_instance = copy.deepcopy(instance)
                        instance.pk = None
                        instance.save()

                        if exceptions_main_tax.get(current_instance) is None and not exception_cleared:
                            exceptions_main_tax.update({current_instance: instance})

                        parent_entry = copy.deepcopy(instance)

                        has_new_bands = False
                        for field in request.POST:
                            if f'additional-{form_number}-' in field:
                                has_new_bands = True
                                break

                        if has_new_bands:
                            for key, value in request.POST.items():
                                if f'band_1_start-additional-{form_number}-' in key and value != "":
                                    instance.band_1_start = value
                                    continue
                                if f'band_1_end-additional-{form_number}-' in key and value != "":
                                    instance.band_1_end = value
                                    continue
                                if f'band_2_start-additional-{form_number}-' in key and value != "":
                                    instance.band_2_start = value
                                    continue
                                if f'band_2_end-additional-{form_number}-' in key and value != "":
                                    instance.band_2_end = value
                                    continue
                                if f'amount-additional-{form_number}-' in key:
                                    if charging_method == 'Percentage':
                                        instance.tax_percentage = value
                                    else:
                                        instance.tax_unit_rate = value

                                    instance.parent_entry = parent_entry
                                    child_entries = TaxRuleException.objects.get(
                                        id=current_instance.id).child_entries.all()
                                    instance.pk = None
                                    instance.save()

                                    for entry in child_entries:
                                        if exceptions_main_tax.get(entry) is None and not exception_cleared:
                                            exceptions_main_tax.update({entry: instance})

            if self.source_doc_type == 'agreement':
                new_entries = TaxRuleException.objects.filter(source_agreement=old_document, valid_ufn=True,
                                                              deleted_at__isnull=True,
                                                              taxable_exception__isnull=False)
            else:
                new_entries = TaxRuleException.objects.filter(related_pld=old_document, valid_ufn=True,
                                                              deleted_at__isnull=True,
                                                              taxable_exception__isnull=False)

            for entry in new_entries:
                if entry.taxable_exception is not None and exceptions_main_tax.get(entry.taxable_exception) is not None:
                    entry.taxable_exception = exceptions_main_tax[entry.taxable_exception]
                    entry.save()

            if request.session.get(f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data'):
                del request.session[f'{self.source_doc_type}-{old_document.pk}-supplier_tax_data']

            request.session[f'{self.source_doc_type}-{self.session_doc_pk}-supplier-defined-taxes-saved'] = True

            messages.success(request, 'Supplier-Defined Taxes saved successfully')

            return HttpResponseRedirect(self.return_url)
        else:

            response_dict = {
                'exception_entity_list': {},
                'official_mismatch': {},
                'exception_mismatch': {},
                'associated_fee_saved': request.session.get(f'{self.source_doc_type}-{self.session_doc_pk}-associated-fee-saved', None),
                'document': old_document,
                'new_document': new_document,
                'document_type': self.source_doc_type,
                'tax_rule_exception_formset': tax_rule_exception_formset,
                'update_date_form': update_date_form
            }

            for form_number, form in enumerate(tax_rule_exception_formset):
                if form.cleaned_data.get(f'form-{form_number}-official_mismatch'):
                    response_dict['show_modal'] = True
                    response_dict['official_mismatch'].update({
                        f'{form_number + 1}': form.cleaned_data.get(f'form-{form_number}-official_mismatch')
                    })

                if form.cleaned_data.get(f'form-{form_number}-exception_mismatch'):
                    response_dict['show_modal'] = True
                    response_dict['exception_mismatch'].update({
                        f'{form_number + 1}': form.cleaned_data.get(f'form-{form_number}-exception_mismatch')
                    })

            for form_number, form in enumerate(tax_rule_exception_formset):
                if form.cleaned_data.get(f'form-{form_number}-exception_entity_list'):
                    response_dict['show_modal'] = True
                    exception_entity_list = form.cleaned_data.get(f'form-{form_number}-exception_entity_list')
                    for entry in exception_entity_list:
                        if entry in response_dict['official_mismatch'].values() \
                            or entry in response_dict['exception_mismatch'].values():
                            exception_entity_list.remove(entry)

                    if exception_entity_list:
                        response_dict['exception_entity_list'].update({
                            f'{form_number + 1}': exception_entity_list
                        })

            if any([form.cleaned_data.get(f'form-{form_number}-official_mismatch'),
                    form.cleaned_data.get(f'form-{form_number}-exception_mismatch'),
                    form.cleaned_data.get(f'form-{form_number}-exception_entity_list')]):
                messages.warning(request, 'Mismatch with associated tax entries')

            else:
                messages.error(request, 'Error found in submitted form')

        return self.render_to_response(response_dict)
