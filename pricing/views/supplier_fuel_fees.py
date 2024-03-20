from datetime import date, datetime, time, timedelta
import json
import re

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, DetailView
from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from pricing.forms import ArchivalForm, NewCombinedFuelFeeRateFormset, PricingDatesSupersedeForm, \
    SupplierFeeRateForm, SupplierFeeRateFormset, SupplierFeesFormset
from pricing.models import FuelPricingMarketPld, FuelPricingMarketPldLocation, SupplierFuelFee, SupplierFuelFeeRate
from pricing.utils import get_datatable_fees_action_btns
from pricing.utils.session import serialize_request_data
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin


# Associated Fees
class SupplierFeesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFeeRate
    search_values_separator = '+'
    initial_order = [['supplier_fuel_fee', "asc"]]
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': SupplierFuelFeeRate.objects.get(id=pk),
            'table_name': 'associated_fees',
            'table_url': reverse_lazy('admin:associated_fees_sublist_ajax', kwargs={
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
            qs = agreement.display_fees
        else:
            document = FuelPricingMarketPld.objects.get(id=self.kwargs['pk'])
            locations = FuelPricingMarketPldLocation.objects.filter(pld=self.kwargs['pk']).values('location')

            qs = SupplierFuelFeeRate.objects.with_location().filter(
                Q(price_active=True),
                Q(supplier_fuel_fee__supplier=document.supplier),
                Q(supplier_fuel_fee__related_pld=document),
                Q(supplier_fuel_fee__location__in=locations),
                Q(Q(quantity_band_start=1) | Q(
                    quantity_band_start=None)),
                Q(Q(weight_band_start=1) | Q(
                    weight_band_start=None))
            )

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
         'orderable': False, 'width': '10px'},
        ### Sort helper columns
        {'name': 'supplier_fuel_fee', 'title': 'Fuel Fee ID', 'visible': False,
         'orderable': True, },
        ### Sort helper columns
        {'name': 'local_name', 'title': 'Name', 'foreign_field': 'supplier_fuel_fee__local_name'},
        {'name': 'icao_iata', 'title': 'Location', 'placeholder': True},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'supplier_fuel_fee__fuel_fee_category__name'},
        {'name': 'specific_fuel', 'title': 'Fuel', 'lookup_field': '__name__icontains'},
        {'name': 'destination_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'pricing_native_amount', 'title': 'Fee', 'orderable': True},
        {'name': 'valid_from_date', 'title': 'Valid From', 'orderable': True},
        {'name': 'actions', 'title': '',
         'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]
        if 'pricing_native_amount' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.distinct('supplier_fuel_fee').order_by('supplier_fuel_fee')
            else:
                qs = qs.distinct('supplier_fuel_fee').order_by('-supplier_fuel_fee')
            return qs
        elif 'destination_type' in orders:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee') \
                .distinct('destination_type__name', 'supplier_fuel_fee')
            return qs
        elif 'flight_type' in orders:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee') \
                .distinct('flight_type__name', 'supplier_fuel_fee')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee') \
                .distinct(orders[0], 'supplier_fuel_fee')
            return qs

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_value = column_link.search_value

                if column_link.name == 'category':
                    qs = qs.filter(Q(supplier_fuel_fee__fuel_fee_category__name__icontains=search_value)).distinct()

                if column_link.name == 'operated_as':
                    if column_link.search_value == '0':
                        qs = qs.filter(applies_to_commercial=True)
                    elif column_link.search_value == '1':
                        qs = qs.filter(applies_to_private=True)
                    elif column_link.search_value == '2':
                        qs = qs.filter(applies_to_commercial=True, applies_to_private=True)

                elif column_link.name == 'pricing_native_amount':
                    if 'bands apply'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(quantity_band_uom=None) | ~Q(weight_band=None))
                    elif 'quantity band applies'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(quantity_band_uom=None), Q(weight_band=None))
                    elif 'weight band applies'.startswith(search_value.lower()):
                        qs = qs.filter(Q(quantity_band_uom=None), ~Q(weight_band=None))
                    else:
                        qs = qs.filter(Q(Q(quantity_band_uom=None), Q(weight_band=None)),
                                       Q(pricing_native_unit__description__icontains=search_value) |
                                       Q(pricing_converted_unit__description__icontains=search_value)
                                       ).distinct()
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs.distinct()

    def customize_row(self, row, obj):

        entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=obj.supplier_fuel_fee, deleted_at__isnull=True)

        if entries.count() > 1 or obj.quantity_band_uom or obj.weight_band:
            add_class = 'has_children'
            if obj.quantity_band_uom is not None and obj.weight_band is not None:
                row['pricing_native_amount'] = 'Bands Apply'
            elif obj.quantity_band_uom is not None:
                row['pricing_native_amount'] = 'Quantity Band Applies'
            elif obj.weight_band is not None:
                row['pricing_native_amount'] = 'Weight Band Applies'
        else:
            add_class = ''
            row['pricing_native_amount'] = obj.get_pricing_datatable_str()

        row['local_name'] = f'<span class="{add_class}"\>{obj.supplier_fuel_fee.local_name}</span>'

        row['valid_from_date'] = obj.valid_from_date

        if obj.specific_fuel is None:
            row['specific_fuel'] = 'All Fuel Types'

        formatted_flight_type = (obj.flight_type.name).split('Only')[0].strip()
        if formatted_flight_type[-1] != 's': formatted_flight_type += 's'

        row['flight_type'] = formatted_flight_type

        url_obj = entries.order_by('quantity_band_start', 'weight_band_start').first()

        if self.source_doc_type == 'agreement':
            view_url = reverse_lazy(
                'admin:agreement_supplier_fee_details',
                kwargs={'pk': url_obj.pk, 'agreement_pk': self.kwargs['pk']})
            edit_url = reverse_lazy(
                'admin:agreement_supplier_fee_edit',
                kwargs={'pk': url_obj.pk, 'agreement_pk': self.kwargs['pk']})
            supersede_url = reverse_lazy(
                'admin:agreement_supplier_fee_supersede',
                kwargs={'pk': url_obj.pk, 'agreement_pk': self.kwargs['pk']})
            archive_url = reverse_lazy(
                'admin:agreement_supplier_fee_archive',
                kwargs={'pk': url_obj.pk})
        else:
            view_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_details',
                kwargs={'pk': url_obj.pk, 'pld': self.kwargs['pk']})
            edit_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_edit',
                kwargs={'pk': url_obj.pk, 'pld': self.kwargs['pk']})
            supersede_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_supersede_associated_fee',
                kwargs={'pk': url_obj.pk, 'pld': self.kwargs['pk']})
            archive_url = reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_archive',
                kwargs={'pk': url_obj.pk})

        row['actions'] = get_datatable_fees_action_btns({
            'view_url': view_url,
            'view_perm': 'pricing.p_view',
            'edit_url': edit_url,
            'edit_perm': 'pricing.p_update',
            'archive_url': archive_url,
            'archive_perm': 'pricing.p_update',
            'supersede_url': supersede_url,
            'supersede_perm': 'pricing.p_create',
        }, self.request)

        return


class SupplierFeesSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFeeRate
    search_values_separator = '+'
    initial_order = [['quantity_band_start', "asc"]]
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'

    def get_initial_queryset(self, request=None):
        parent_entry = SupplierFuelFeeRate.objects.get(id=self.kwargs['pk'])
        qs = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=parent_entry.supplier_fuel_fee)

        if self.source_doc_type == 'pld':
            qs = qs.filter(price_active=True)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'quantity_band_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'weight_band_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'pricing_native_amount', 'title': 'Native Pricing', 'placeholder': True},
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

        if obj.quantity_band_start is not None:
            row['quantity_band_start'] = f'{obj.quantity_band_uom}: \
                                           {int(obj.quantity_band_start)} - {int(obj.quantity_band_end)}'

        if obj.weight_band_start is not None:
            row['weight_band_start'] = f'{obj.weight_band}: \
                                         {int(obj.weight_band_start)} - {int(obj.weight_band_end)}'

        row['pricing_native_amount'] = obj.get_pricing_datatable_str(for_sublist=True)


class SupplierFeeDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'supplier_fee_details.html'
    model = SupplierFuelFeeRate
    context_object_name = 'entry'
    permission_required = ['pricing.p_view']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'agreement_pk' in self.kwargs else 'pld'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = SupplierFuelFeeRate.objects.get(id=self.kwargs['pk'])

        if self.source_doc_type == 'agreement':
            related_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=instance.supplier_fuel_fee) \
                .order_by('quantity_band_start')
            document = FuelAgreement.objects.get(id=self.kwargs['agreement_pk'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement',
                                         kwargs={'pk': document.id}),
                'source_doc_url': reverse_lazy('admin:fuel_agreement',
                                               kwargs={'pk': document.id}),
                'edit_url': reverse_lazy('admin:agreement_supplier_fee_edit',
                                         kwargs={'pk': self.object.pk, 'agreement_pk': document.pk}),
                'supersede_url': reverse_lazy('admin:agreement_supplier_fee_supersede',
                                         kwargs={'pk': self.object.pk, 'agreement_pk': document.pk}),
            }
        else:
            related_entries = SupplierFuelFeeRate.objects.filter(price_active=True,
                                                                 supplier_fuel_fee=instance.supplier_fuel_fee) \
                .order_by('quantity_band_start')
            document = FuelPricingMarketPld.objects.get(id=self.kwargs['pld'])
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details',
                                         kwargs={'pk': document.id}),
                'source_doc_url': reverse_lazy('admin:fuel_pricing_market_document_details',
                                               kwargs={'pk': document.id}),
                'edit_url': reverse_lazy('admin:fuel_pricing_market_documents_associated_fee_edit',
                                         kwargs={'pk': self.object.pk, 'pld': document.id}),
                'supersede_url': reverse_lazy('admin:fuel_pricing_market_documents_supersede_associated_fee',
                                         kwargs={'pk': self.object.pk, 'pld': document.id}),
            }

        context['document_type'] = self.source_doc_type
        context['document'] = document
        context['related_entries'] = related_entries
        context['metacontext'] = metacontext

        return context


class SupplierFeesCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_fees_create.html'
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

        extra_location_fields = {i: 0 for i in range(10)}
        extra_period_fields = {i: 0 for i in range(10)}

        combined_fuel_fee_formset = NewCombinedFuelFeeRateFormset(
            form_kwargs={'doc_instance': document, 'doc_type': self.source_doc_type},
            doc_instance=document, doc_type=self.source_doc_type,
            extra_location_fields=extra_location_fields,
            extra_period_fields=extra_period_fields,
            prefix='new-fuel-fee-rate', context='Create')

        if self.source_doc_type == 'agreement':
            locations = document.pricing_formulae.all().values('location') \
                .union(document.pricing_manual.all().values('location'))
        else:
            locations = document.pld_at_location.all().values('location')

        # We can filter for all fuel fees, even if it is a tax, it is no longer a new PLD
        if self.source_doc_type == 'agreement':
            fuel_fee_entries = SupplierFuelFeeRate.objects.filter(
                source_agreement=document)
        else:
            fuel_fee_entries = SupplierFuelFeeRate.objects.filter(
                price_active=True,
                supplier_fuel_fee__location__in=locations,
                supplier_fuel_fee__supplier=document.supplier,
                supplier_fuel_fee__related_pld=document)

        new_doc = False
        if request.session.get(f'{self.source_doc_type}-{document.id}') and not fuel_fee_entries.exists():
            new_doc = True

        return self.render_to_response({
            'doc_is_new': new_doc,
            'doc_instance': document,
            'combined_fuel_fee_formset': combined_fuel_fee_formset
        })

    def post(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pk'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.load(request)
            form_number = int(data['form_number'])
            new_field_number = int(data['new_field_number'])

            combined_fuel_fee_formset = NewCombinedFuelFeeRateFormset(form_kwargs={
                'doc_instance': document, 'doc_type': self.source_doc_type},
                doc_instance=document, doc_type=self.source_doc_type,
                prefix='new-fuel-fee-rate', context='Create')

            combined_fuel_fee_formset.create_ipa_field(combined_fuel_fee_formset[form_number], form_number,
                                                       new_field_number)
            combined_fuel_fee_formset.create_handler_field(combined_fuel_fee_formset[form_number], form_number,
                                                           new_field_number)

            return render(request,
                          'pricing_pages_includes/_pricing_market_updates_associated_fee_location_fields.html',
                          context={
                              'form': combined_fuel_fee_formset[form_number],
                              'ipa_field': combined_fuel_fee_formset[form_number][
                                  f'ipa-additional-{new_field_number}'],
                              'handler_field': combined_fuel_fee_formset[form_number][
                                  f'specific_handler-additional-{new_field_number}']})

        expected_forms = int(request.POST.get('new-fuel-fee-rate-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields.keys():
            for key in request.POST:
                if f'quantity_band_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        extra_location_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields.keys():
            for key in request.POST:
                if f'-{form_number}-location-additional' in key:
                    extra_location_fields[form_number] += 1

        extra_period_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields.keys():
            for key in request.POST:
                if f'-{form_number}-valid_from_dow-additional' in key:
                    extra_period_fields[form_number] += 1

        combined_fuel_fee_formset = NewCombinedFuelFeeRateFormset(request.POST,
                                                                  form_kwargs={'doc_instance': document,
                                                                               'doc_type': self.source_doc_type},
                                                                  doc_instance=document, doc_type=self.source_doc_type,
                                                                  extra_fields=extra_fields,
                                                                  extra_location_fields=extra_location_fields,
                                                                  extra_period_fields=extra_period_fields,
                                                                  prefix='new-fuel-fee-rate', context='Create')

        if 'skip' in request.POST['button-pressed']:
            if self.source_doc_type == 'agreement':
                return HttpResponseRedirect(reverse_lazy('admin:agreement_supplier_tax_create',
                                                         kwargs={'agreement_pk': document.id}))
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_create_page',
                                 kwargs={'pk': document.id}))

        if self.source_doc_type == 'agreement':
            fuel_fee_entries = SupplierFuelFeeRate.objects.filter(
                source_agreement=document)
        else:
            locations = document.pld_at_location.all().values('location')
            fuel_fee_entries = SupplierFuelFeeRate.objects.filter(
                price_active=True,
                supplier_fuel_fee__location__in=locations,
                supplier_fuel_fee__related_pld=document,
                supplier_fuel_fee__supplier=document.supplier)

        new_doc = False
        if request.session.get(f'{self.source_doc_type}-{document.id}') and not fuel_fee_entries.exists():
            new_doc = True

        if all([
            combined_fuel_fee_formset.is_valid(),
        ]):
            with transaction.atomic():

                new_fuel_fees = combined_fuel_fee_formset.save(commit=False)

                for form_num, form in enumerate(combined_fuel_fee_formset):
                    if form.has_changed() and not form.cleaned_data.get('DELETE'):
                        instance = form.save(commit=False)
                        created_fees = []
                        hookup_method = form.cleaned_data.get('specific_hookup_method')

                        for field, value in form.cleaned_data.items():
                            if f'location' in field and value is not None:
                                current_row = re.findall("\d+", field)

                                if not current_row:
                                    ipa_field = form.cleaned_data.get('ipa')
                                    pricing_unit_field = form.cleaned_data.get('pricing_native_unit')
                                    handler_field = form.cleaned_data.get('specific_handler')
                                    handler_is_excluded = form.cleaned_data.get('specific_handler_is_excluded')
                                    apron_field = form.cleaned_data.get('specific_apron')
                                else:
                                    current_row = current_row[0]
                                    ipa_field = form.cleaned_data.get(f'ipa-additional-{current_row}')
                                    pricing_unit_field = form.cleaned_data.get(
                                        f'pricing_native_unit-additional-{current_row}')
                                    handler_field = form.cleaned_data.get(f'specific_handler-additional-{current_row}')
                                    handler_is_excluded = bool(
                                        form.cleaned_data.get(f'specific_handler_is_excluded-additional-{current_row}',
                                                              False))
                                    apron_field = form.cleaned_data.get(f'specific_apron-additional-{current_row}')

                                if self.source_doc_type == 'agreement':
                                    new_fee = SupplierFuelFee.objects.create(
                                        local_name=form.cleaned_data.get('local_name'),
                                        supplier=document.supplier,
                                        location=value,
                                        ipa=ipa_field,
                                        fuel_fee_category=form.cleaned_data.get('fuel_fee_category'),
                                        pricing_unit=pricing_unit_field,
                                    )
                                    instance.source_agreement = document
                                else:
                                    new_fee = SupplierFuelFee.objects.create(
                                        local_name=form.cleaned_data.get('local_name'),
                                        supplier=document.supplier,
                                        location=value,
                                        ipa=ipa_field,
                                        fuel_fee_category=form.cleaned_data.get('fuel_fee_category'),
                                        pricing_unit=pricing_unit_field,
                                        related_pld=document,
                                    )

                                created_fees.append(new_fee)

                                instance.supplier_fuel_fee = new_fee
                                instance.pricing_native_unit = pricing_unit_field
                                instance.specific_handler = handler_field
                                instance.specific_handler_is_excluded = handler_is_excluded
                                instance.specific_apron = apron_field
                                instance.specific_hookup_method = hookup_method
                                instance.updated_by = request.user.person

                                if extra_fields[form_num] != 0:
                                    for key, value in request.POST.items():
                                        if f'-{form_num}-quantity_band_start' in key and value != "":
                                            instance.quantity_band_start = value
                                            continue
                                        if f'-{form_num}-quantity_band_end' in key and value != "":
                                            instance.quantity_band_end = value
                                            continue
                                        if f'-{form_num}-weight_band_start' in key and value != "":
                                            instance.weight_band_start = value
                                            continue
                                        if f'-{form_num}-weight_band_end' in key and value != "":
                                            instance.weight_band_end = value
                                            continue
                                        if f'-{form_num}-band_pricing' in key:
                                            instance.pricing_native_amount = value

                                            if instance.supplier_exchange_rate:
                                                instance.convert_pricing_amount()

                                            instance.save()
                                            instance.pk = None
                                else:
                                    band_pricing = \
                                        request.POST.get(f'new-fuel-fee-rate-{form_num}-band_pricing_native_amount')

                                    if band_pricing:
                                        instance.pricing_native_amount = band_pricing
                                        instance.save()
                                        instance.pk = None
                                    else:
                                        if current_row:
                                            instance.pricing_native_amount = \
                                                form.cleaned_data.get(f'pricing_native_amount-additional-{current_row}')
                                        # Else it is already associated with instance

                                        if instance.supplier_exchange_rate:
                                            instance.convert_pricing_amount()

                                        instance.save()
                                        instance.pk = None

                        # Attach validity period to saved rates
                        new_periods = []

                        for key, value in form.cleaned_data.items():
                            if f'valid_from_dow' in key and value != "":
                                row_index = int(
                                    re.search(r'\d+$', key).group()) if 'additional' in key else 0
                                row_suffix = f'-additional-{row_index}' if row_index > 0 else ''

                                is_local = bool(form.cleaned_data.get(f'is_local'))
                                from_dow = int(value)
                                to_dow = int(form.cleaned_data.get(f'valid_to_dow{row_suffix}'))
                                from_time = form.cleaned_data.get(f'valid_from_time{row_suffix}')
                                to_time = form.cleaned_data.get(f'valid_to_time{row_suffix}')
                                all_day = form.cleaned_data.get(f'valid_all_day{row_suffix}')

                                if all_day:
                                    from_time = time(0, 0, 0)
                                    to_time = time(23, 59, 59)
                                else:
                                    from_time = from_time
                                    to_time = to_time.replace(second=59)

                                new_periods.append((from_dow, to_dow, from_time, to_time, is_local))

                        for fee in created_fees:
                            for rate in fee.rates.all():
                                rate.update_validity_periods(new_periods)

                messages.success(request, 'Associated Fee saved successfully')

                if self.source_doc_type == 'agreement':
                    if new_doc:
                        return HttpResponseRedirect(
                            reverse_lazy('admin:agreement_supplier_tax_create',
                                         kwargs={'agreement_pk': document.id}))
                    elif request.session.get(f'{self.source_doc_type}-{document.id}-associated_fees_data'):
                        request.session.pop(f'{self.source_doc_type}-{document.id}-associated_fees_data')
                        return HttpResponseRedirect(
                            reverse_lazy('admin:agreement_supplier_fees_supersede',
                                         kwargs={'pk': document.superseded_by.pk}))
                    else:
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                                 kwargs={'pk': document.id}))
                else:
                    if new_doc:
                        return HttpResponseRedirect(
                            reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_create_page',
                                         kwargs={'pk': document.id}))
                    elif request.session.get(f'{self.source_doc_type}-{document.id}-associated_fees_data'):
                        request.session.pop(f'{self.source_doc_type}-{document.id}-associated_fees_data')
                        return HttpResponseRedirect(
                            reverse_lazy('admin:fuel_pricing_market_documents_supersede_associated_fees',
                                         kwargs={'pk': document.id}))
                    else:
                        return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                                 kwargs={'pk': document.id}))

        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'doc_is_new': new_doc,
                'doc_instance': document,
                'combined_fuel_fee_formset': combined_fuel_fee_formset,
            })


class SupplierFeeEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_fee_edit.html'
    permission_required = ['pricing.p_update']
    source_doc_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'agreement_pk' in self.kwargs else 'pld'

    def get(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
            entry = SupplierFuelFeeRate.objects.filter(id=self.kwargs['pk'])
            related_entries = SupplierFuelFeeRate.objects.filter(Q(supplier_fuel_fee=entry[0].supplier_fuel_fee),
                                                                 ~Q(id__in=entry))
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement', kwargs={'pk': document.id})
            }
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])
            entry = SupplierFuelFeeRate.objects.filter(id=self.kwargs['pk'], price_active=True)
            related_entries = SupplierFuelFeeRate.objects.filter(Q(supplier_fuel_fee=entry[0].supplier_fuel_fee),
                                                                 ~Q(id__in=entry), Q(price_active=True))
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': document.id})
            }

        existing_periods = entry[0].validity_periods_sorted

        fuel_fee_formset = SupplierFeesFormset(
            form_kwargs={'doc_instance': document, 'doc_type': self.source_doc_type,
                         'context': 'Edit', 'entry': entry},
            doc_instance=document, entry=entry, context='Edit',
            doc_type=self.source_doc_type,
            prefix='fuel-fee')

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            form_kwargs={'doc_instance': document, 'doc_type': self.source_doc_type,
                         'context': 'Edit'},
            context='Edit', entry=entry, related_entries=related_entries,
            existing_periods=existing_periods,
            doc_type=self.source_doc_type, doc_instance=document,
            prefix='fuel-fee-rate', fee_formset=fuel_fee_formset)

        return self.render_to_response({
            'doc_instance': document,
            'fuel_fee_formset': fuel_fee_formset,
            'fuel_fee_rate_formset': fuel_fee_rate_formset,
            'metacontext': metacontext,
        })

    def post(self, request, *args, **kwargs):
        if self.source_doc_type == 'agreement':
            document = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
            entry = SupplierFuelFeeRate.objects.filter(id=self.kwargs['pk'])
            related_entries = SupplierFuelFeeRate.objects.filter(Q(supplier_fuel_fee=entry[0].supplier_fuel_fee),
                                                                 ~Q(id__in=entry))
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_agreement', kwargs={'pk': document.id})
            }
        else:
            document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])
            entry = SupplierFuelFeeRate.objects.filter(id=self.kwargs['pk'], price_active=True)
            related_entries = SupplierFuelFeeRate.objects.filter(Q(supplier_fuel_fee=entry[0].supplier_fuel_fee),
                                                                 Q(price_active=True),
                                                                 ~Q(id__in=entry))
            metacontext = {
                'back_url': reverse_lazy('admin:fuel_pricing_market_document_details', kwargs={'pk': document.id})
            }

        extra_fields = {0: 0}
        extra_period_fields = {0: 0}

        for form_number in extra_fields:
            for key in request.POST:
                if f'quantity_band_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1
                elif f'-{form_number}-valid_from_dow-additional' in key:
                    extra_period_fields[form_number] += 1

        fuel_fee_formset = SupplierFeesFormset(
            request.POST,
            form_kwargs={'doc_instance': document, 'doc_type': self.source_doc_type,
                         'context': 'Edit', 'entry': entry},
            doc_type=self.source_doc_type, doc_instance=document,
            entry=entry, prefix='fuel-fee')

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            request.POST,
            form_kwargs={'doc_instance': document, 'doc_type': self.source_doc_type,
                         'context': 'Edit'},
            doc_type=self.source_doc_type,
            doc_instance=document,
            entry=entry, context='Edit', related_entries=related_entries,
            extra_fields=extra_fields,
            extra_period_fields=extra_period_fields,
            prefix='fuel-fee-rate', fee_formset=fuel_fee_formset)

        if all([
            fuel_fee_formset.is_valid(),
            fuel_fee_rate_formset.is_valid(),
        ]):
            with transaction.atomic():

                has_new_bands = False
                for field in request.POST:
                    if 'additional' in field:
                        has_new_bands = True
                        break

                # Note: this is not used strictly as a formset, because we are only editing 1 entity, but this way I can
                # reuse the formset's logic
                for count, form in enumerate(fuel_fee_rate_formset):
                    instance = form.save(commit=False)
                    instance.updated_by = request.user.person
                    instance.supplier_fuel_fee = entry[0].supplier_fuel_fee
                    band_pricing = request.POST.get(f'fuel-fee-rate-{count}-band_pricing_native_amount')
                    existing_entry = 0

                    if form.cleaned_data.get('delivery_method') is None:
                        instance.delivery_method = None

                    if form.cleaned_data.get('specific_fuel') is None:
                        instance.specific_fuel = None

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    if band_pricing:
                        instance.pricing_native_amount = band_pricing

                    if instance.supplier_exchange_rate:
                        instance.convert_pricing_amount()

                    instance.save()

                    # Save new bands as new instances
                    if has_new_bands:
                        instance.pk = None

                        for key, value in request.POST.items():
                            if f'quantity_band_start-additional' in key and value != "":
                                instance.quantity_band_start = value
                                continue
                            if f'quantity_band_end-additional' in key and value != "":
                                instance.quantity_band_end = value
                                continue
                            if f'weight_band_start-additional' in key and value != "":
                                instance.weight_band_start = value
                                continue
                            if f'weight_band_end-additional' in key and value != "":
                                instance.weight_band_end = value
                                continue
                            if f'amount-additional' in key:
                                instance.pricing_native_amount = value

                                if instance.supplier_exchange_rate:
                                    instance.convert_pricing_amount()
                                if existing_entry < related_entries.count():
                                    instance.pk = related_entries[existing_entry].pk
                                    instance.save()
                                    existing_entry += 1
                                else:
                                    instance.save()

                                instance.pk = None

                    # Delete the remaining
                    # I assume it is OK to delete in this case, as to not litter the database with wrongful entries
                    # and only set price as inactive on supersede as to preserve the history
                    while existing_entry < related_entries.count():
                        instance_to_delete = related_entries[existing_entry]
                        instance_to_delete.delete()
                        existing_entry += 1

                for form in fuel_fee_formset:
                    fuel_fee = form.save(commit=False)
                    fuel_fee.id = entry[0].supplier_fuel_fee_id

                    if self.source_doc_type == 'pld':
                        fuel_fee.related_pld = document

                    fuel_fee.pricing_unit = instance.pricing_native_unit
                    fuel_fee.ipa = form.cleaned_data.get('custom_ipa')
                    fuel_fee.save()

                # Attach validity period to saved rates
                for form in fuel_fee_rate_formset:
                    new_periods = []

                    for key, value in request.POST.items():
                        if f'valid_from_dow' in key and value != "":
                            row_index = int(re.search(r'\d+$', key).group()) if 'additional' in key else 0
                            row_suffix = f'-additional-{row_index}' if row_index > 0 else ''

                            is_local = bool(request.POST.get(f'{form.prefix}-is_local'))
                            from_dow = int(value)
                            to_dow = int(request.POST.get(f'{form.prefix}-valid_to_dow{row_suffix}'))
                            from_time = request.POST.get(f'{form.prefix}-valid_from_time{row_suffix}')
                            to_time = request.POST.get(f'{form.prefix}-valid_to_time{row_suffix}')
                            all_day = request.POST.get(f'{form.prefix}-valid_all_day{row_suffix}')

                            if all_day:
                                from_time = time(0, 0, 0)
                                to_time = time(23, 59, 59)
                            else:
                                from_time = datetime.strptime(from_time, '%H:%M').time()
                                to_time = datetime.strptime(to_time, '%H:%M').time().replace(second=59)

                            new_periods.append((from_dow, to_dow, from_time, to_time, is_local))

                    for rate in form.instance.supplier_fuel_fee.rates.all():
                        rate.update_validity_periods(new_periods)

                messages.success(request, 'Associated Fee updated successfully')

                if self.source_doc_type == 'agreement':
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                             kwargs={'pk': document.id}))
                else:
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                             kwargs={'pk': document.id}))

        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'doc_instance': document,
                'fuel_fee_formset': fuel_fee_formset,
                'fuel_fee_rate_formset': fuel_fee_rate_formset,
                'metacontext': metacontext,
            })


class SupplierFeeArchiveView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'pricing_pages_includes/_modal_delete_tax_form.html'
    model = SupplierFuelFeeRate
    form_class = ArchivalForm
    success_message = 'Entry archived successfully'
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
            'title': 'Archive Fuel Fee Entry',
            'text': 'Are you sure you want to archive this fuel fee?',
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':

            main_entry = SupplierFuelFeeRate.objects.get(id=self.kwargs['pk'])

            if self.source_doc_type == 'agreement':
                all_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=main_entry.supplier_fuel_fee)
            else:
                all_entries = SupplierFuelFeeRate.objects.filter(price_active=True,
                                                                 supplier_fuel_fee=main_entry.supplier_fuel_fee)

            form_valid_to = form.cleaned_data.get('valid_to')
            time_now = datetime.now()

            for entry in all_entries:
                entry.price_active = False
                entry.deleted_at = time_now
                entry.valid_to_date = form_valid_to - timedelta(days=1)
                entry.updated_by = self.request.user.person
                entry.save()

        return super().form_valid(form)


class SupplierFeeSupersedeView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_fees_supersede.html'
    permission_required = ['pricing.p_create']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_doc_type = 'agreement' if 'fuel_agreement' in self.request.path else 'pld'
        self.existing_fee_pk = self.kwargs.get('pk', None)

        if self.source_doc_type == 'agreement':
            self.document = FuelAgreement.objects.get(pk=self.kwargs.get('agreement_pk', None))
            self.return_url = reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.document.pk})
        else:
            self.document = FuelPricingMarketPld.objects.get(pk=self.kwargs.get('pld', None))
            self.return_url = reverse_lazy('admin:fuel_pricing_market_document_details',
                                           kwargs={'pk': self.document.pk})

    def get(self, request, *args, **kwargs):
        old_document = self.document
        new_document = self.document

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            form_kwargs={'doc_instance': old_document, 'new_doc_instance': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            doc_instance=old_document, new_doc_instance=new_document, doc_type=self.source_doc_type,
            context='Supersede', prefix='existing-fuel-fee-rate', single_fee_pk=self.existing_fee_pk)

        return self.render_to_response({
            'document': old_document,
            'new_document': new_document,
            'document_type': self.source_doc_type,
            'fuel_fee_rate_formset': fuel_fee_rate_formset,
            'card_title': 'Existing Fee Details',
            'single_fee_mode': True,
            'fee': get_object_or_404(SupplierFuelFeeRate, pk=self.existing_fee_pk).supplier_fuel_fee
        })

    def post(self, request, *args, **kwargs):
        old_document = self.document
        new_document = self.document

        form_numbers = request.POST.get('existing-fuel-fee-rate-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        extra_period_fields = {i: 0 for i in range(int(form_numbers))}

        for form_number in extra_fields:
            for key in request.POST:
                if f'-{form_number}-quantity_band_start-additional' in key:
                    extra_fields[form_number] += 1
                elif f'-{form_number}-valid_from_dow-additional' in key:
                    extra_period_fields[form_number] += 1

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            request.POST,
            form_kwargs={'doc_instance': old_document, 'new_doc_instance': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            doc_instance=old_document, new_doc_instance=new_document, doc_type=self.source_doc_type,
            context='Supersede', extra_fields=extra_fields, extra_period_fields=extra_period_fields,
            prefix='existing-fuel-fee-rate', single_fee_pk=self.existing_fee_pk)

        if all([
            fuel_fee_rate_formset.is_valid(),
        ]):
            with transaction.atomic():

                fuel_fee_rate_formset.save(commit=False)

                for count, form in enumerate(fuel_fee_rate_formset):
                    instance = form.save(commit=False)
                    valid_from = instance.valid_from_date

                    # Store all existing entries
                    all_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=instance.supplier_fuel_fee)
                    time_now = datetime.now()

                    for entry in all_entries:
                        entry.updated_by = request.user.person
                        entry.valid_to_date = valid_from - timedelta(days=1)
                        entry.price_active = False
                        entry.deleted_at = time_now
                        entry.save()

                    # New Fuel Fee entry - document association - history keeping
                    new_fuel_fee_entry = SupplierFuelFee.objects.get(id=instance.supplier_fuel_fee.id)

                    if self.source_doc_type == 'pld':
                        new_fuel_fee_entry.related_pld = old_document

                    new_fuel_fee_entry.id = None
                    new_fuel_fee_entry.save()

                    # New Fuel Fee Rates
                    related_entries = SupplierFuelFeeRate.objects. \
                        filter(supplier_fuel_fee=instance.supplier_fuel_fee) \
                        .order_by('quantity_band_start', 'weight_band_start')

                    parent_entry = related_entries[0]

                    if parent_entry.supplier_exchange_rate is not None:
                        instance.convert_pricing_amount()

                    if form.cleaned_data.get('delivery_method') is None:
                        instance.delivery_method = None

                    if form.cleaned_data.get('specific_fuel') is None:
                        instance.specific_fuel = None

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    instance.supplier_fuel_fee = new_fuel_fee_entry
                    instance.valid_from_date = valid_from
                    instance.valid_to_date = None

                    if self.source_doc_type == 'agreement':
                        instance.price_active = self.document.is_active
                        instance.source_agreement = self.document
                    else:
                        instance.price_active = True

                    instance.pk = None
                    instance.save()

                    for key, value in request.POST.items():
                        if f'quantity_band_start-additional-{count}-' in key and value != "":
                            instance.quantity_band_start = value
                            continue
                        if f'quantity_band_end-additional-{count}-' in key and value != "":
                            instance.quantity_band_end = value
                            continue
                        if f'weight_band_start-additional-{count}-' in key and value != "":
                            instance.weight_band_start = value
                            continue
                        if f'weight_band_end-additional-{count}-' in key and value != "":
                            instance.weight_band_end = value
                            continue
                        if f'amount-additional-{count}-' in key:
                            instance.pricing_native_amount = value

                            if parent_entry.supplier_exchange_rate is not None:
                                instance.convert_pricing_amount()

                            if self.source_doc_type == 'agreement':
                                entry.source_agreement = self.document

                            instance.pk = None
                            instance.save()

                # Attach validity period to saved rates
                for form in fuel_fee_rate_formset:
                    new_periods = []

                    for key, value in request.POST.items():
                        if f'{form.prefix}-valid_from_dow' in key and value != "":
                            row_index = int(re.search(r'\d+$', key).group()) if 'additional' in key else 0
                            row_suffix = f'-additional-{row_index}' if row_index > 0 else ''

                            is_local = bool(request.POST.get(f'{form.prefix}-is_local'))
                            from_dow = int(value)
                            to_dow = int(request.POST.get(f'{form.prefix}-valid_to_dow{row_suffix}'))
                            from_time = request.POST.get(f'{form.prefix}-valid_from_time{row_suffix}')
                            to_time = request.POST.get(f'{form.prefix}-valid_to_time{row_suffix}')
                            all_day = request.POST.get(f'{form.prefix}-valid_all_day{row_suffix}')

                            if all_day:
                                from_time = time(0, 0, 0)
                                to_time = time(23, 59, 59)
                            else:
                                from_time = datetime.strptime(from_time, '%H:%M').time()
                                to_time = datetime.strptime(to_time, '%H:%M').time().replace(second=59)

                            new_periods.append((from_dow, to_dow, from_time, to_time, is_local))

                    for rate in form.instance.supplier_fuel_fee.rates.all():
                        rate.update_validity_periods(new_periods)

                messages.success(request, 'Associated Fee superseded successfully')

                return HttpResponseRedirect(self.return_url)
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'document': old_document,
                'new_document': new_document,
                'document_type': self.source_doc_type,
                'fuel_fee_rate_formset': fuel_fee_rate_formset,
                'card_title': 'Existing Fee Details',
                'single_fee_mode': True,
                'fee': get_object_or_404(SupplierFuelFeeRate, pk=self.existing_fee_pk).supplier_fuel_fee
            })


class SupplierFeesSupersedeView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'supplier_fees_supersede.html'
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
            self.supersede_taxes_url = reverse_lazy('admin:agreement_supplier_tax_supersede',
                                                    kwargs={'pk': self.new_document.id})
            self.create_fees_url = reverse_lazy('admin:agreement_supplier_fee_create',
                                                kwargs={'agreement_pk': self.old_document.id})
        else:
            self.new_document = None
            self.old_document = FuelPricingMarketPld.objects.get(pk=self.kwargs.get('pk', None))
            self.session_doc_pk = self.old_document.pk
            self.return_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_pricing',
                                           kwargs={'pk': self.old_document.id})
            self.supersede_pricing_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_pricing',
                                                      kwargs={'pk': self.old_document.id})
            self.supersede_taxes_url = reverse_lazy('admin:fuel_pricing_market_documents_supersede_supplier_taxes',
                                                    kwargs={'pk': self.old_document.id})
            self.create_fees_url = reverse_lazy('admin:fuel_pricing_market_documents_associated_fees_create_page',
                                                kwargs={'pk': self.old_document.id})

    def get(self, request, *args, **kwargs):
        old_document = self.old_document
        new_document = self.new_document

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            form_kwargs={'doc_instance': old_document, 'new_doc_instance': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            doc_instance=old_document, new_doc_instance=new_document, doc_type=self.source_doc_type,
            context='Supersede', prefix='existing-fuel-fee-rate')

        update_date_form = PricingDatesSupersedeForm(prefix='update-date')

        if f'{self.source_doc_type}-{old_document.pk}-associated_fees_data' in request.session:
            session_data = request.session[f'{self.source_doc_type}-{old_document.pk}-associated_fees_data']

            form_numbers = session_data.get('existing-fuel-fee-rate-TOTAL_FORMS')

            extra_fields = {i: 0 for i in range(int(form_numbers))}
            extra_period_fields = {i: 0 for i in range(int(form_numbers))}

            for form_number in extra_fields:
                for key in session_data:
                    if f'-{form_number}-quantity_band_start-additional' in key:
                        extra_fields[form_number] += 1
                    elif f'-{form_number}-valid_from_dow-additional' in key:
                        extra_period_fields[form_number] += 1

            fuel_fee_rate_formset = SupplierFeeRateFormset(data=session_data,
                                                           form_kwargs={'doc_instance': old_document,
                                                                        'new_doc_instance': new_document,
                                                                        'doc_type': self.source_doc_type,
                                                                        'context': 'Supersede'},
                                                           doc_instance=old_document, new_doc_instance=new_document,
                                                           doc_type=self.source_doc_type, context='Supersede',
                                                           extra_fields=extra_fields,
                                                           extra_period_fields=extra_period_fields,
                                                           prefix='existing-fuel-fee-rate')

            for form in fuel_fee_rate_formset:
                if 'delivery_method' not in form.data or form.data.get('delivery_method') is None:
                    form.errors.pop('delivery_method', None)

                if 'delivery_method' not in form.data or form.data.get('specific_fuel') is None:
                    form.errors.pop('specific_fuel', None)

            update_date_form = PricingDatesSupersedeForm(session_data,
                                                         prefix='update-date')

        return self.render_to_response({
            'supplier_defined_tax_saved': request.session.get(f'{self.source_doc_type}-{self.session_doc_pk}-supplier-defined-taxes-saved', None),
            'document': old_document,
            'new_document': new_document,
            'document_type': self.source_doc_type,
            'fuel_fee_rate_formset': fuel_fee_rate_formset,
            'update_date_form': update_date_form
        })

    def post(self, request, *args, **kwargs):
        old_document = self.old_document
        new_document = self.new_document

        form_numbers = request.POST.get('existing-fuel-fee-rate-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        extra_period_fields = {i: 0 for i in range(int(form_numbers))}

        for form_number in extra_fields:
            for key in request.POST:
                if f'-{form_number}-quantity_band_start-additional' in key:
                    extra_fields[form_number] += 1
                elif f'-{form_number}-valid_from_dow-additional' in key:
                    extra_period_fields[form_number] += 1

        fuel_fee_rate_formset = SupplierFeeRateFormset(
            request.POST,
            form_kwargs={'doc_instance': old_document, 'new_doc_instance': new_document,
                         'doc_type': self.source_doc_type, 'context': 'Supersede'},
            doc_instance=old_document, new_doc_instance=new_document, doc_type=self.source_doc_type,
            context='Supersede', extra_fields=extra_fields, extra_period_fields=extra_period_fields,
            prefix='existing-fuel-fee-rate')

        update_date_form = PricingDatesSupersedeForm(request.POST,
                                                     prefix='update-date')

        if request.POST['button-pressed'] != 'save':
            request.session[f'{self.source_doc_type}-{old_document.pk}-associated_fees_data'] = serialize_request_data(request.POST)
            request.session[self.source_doc_type] = self.session_doc_pk

            if 'taxes' in request.POST['button-pressed']:
                messages.info(request, 'Associated Fee form fields were saved')
                return HttpResponseRedirect(self.supersede_taxes_url)

            elif 'fuel-pricing' in request.POST['button-pressed']:
                messages.info(request, 'Associated Fee form fields were saved')
                return HttpResponseRedirect(self.supersede_pricing_url)

            elif 'fuel-fee-create' in request.POST['button-pressed']:
                messages.warning(request, 'Associated Fee form fields\' state will be deleted after new fee creation!')
                return HttpResponseRedirect(self.create_fees_url)

        if all([
            fuel_fee_rate_formset.is_valid(),
            update_date_form.is_valid()
        ]):
            with transaction.atomic():

                fuel_fee_rate_formset.save(commit=False)
                time_now = datetime.now()

                for count, form in enumerate(fuel_fee_rate_formset):
                    instance = form.save(commit=False)
                    no_change = request.POST.get(f'existing-fuel-fee-rate-{count}-no_change')
                    # Using this for expiry, else this is automatically associated with the instance
                    valid_to_date = request.POST.get(f'existing-fuel-fee-rate-{count}-valid_to_date')

                    if update_date_form.cleaned_data.get('valid_from'):
                        valid_from = update_date_form.cleaned_data.get('valid_from')
                    else:
                        valid_from = instance.valid_from_date

                    if instance in fuel_fee_rate_formset.deleted_objects:
                        SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=instance.supplier_fuel_fee) \
                            .update(price_active=False,
                                    deleted_at=time_now,
                                    valid_to_date=valid_to_date,
                                    updated_by=request.user.person)
                        continue

                    # Store all existing entries
                    all_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=instance.supplier_fuel_fee)
                    for entry in all_entries:
                        entry.updated_by = request.user.person
                        entry.price_active = False

                        if no_change == 'on':
                            entry.valid_to_date = time_now - timedelta(days=1)
                        else:
                            entry.valid_to_date = valid_from - timedelta(days=1)

                        entry.save()

                    # New Fuel Fee entry - document association - history keeping
                    new_fuel_fee_entry = SupplierFuelFee.objects.get(id=instance.supplier_fuel_fee.id)

                    if self.source_doc_type == 'pld':
                        new_fuel_fee_entry.related_pld = old_document

                    new_fuel_fee_entry.id = None
                    new_fuel_fee_entry.save()

                    if no_change == 'on':
                        all_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee=instance.supplier_fuel_fee) \
                            .order_by('quantity_band_start', 'weight_band_start')

                        if all_entries.exists():
                            for entry in all_entries:
                                entry.supplier_fuel_fee = new_fuel_fee_entry
                                entry.updated_by = request.user.person
                                entry.valid_from_date = date.today()
                                entry.valid_to_date = None

                                if self.source_doc_type == 'agreement':
                                    entry.price_active = self.new_document.is_active
                                    entry.source_agreement = self.new_document

                                entry.pk = None
                                entry.save()

                                # Update form instance (needed to correctly assign validity periods below)
                                form.instance = entry
                    else:
                        # New Fuel Fee Rates
                        related_entries = SupplierFuelFeeRate.objects. \
                            filter(supplier_fuel_fee=instance.supplier_fuel_fee) \
                            .order_by('quantity_band_start', 'weight_band_start')

                        parent_entry = related_entries[0]

                        if parent_entry.supplier_exchange_rate is not None:
                            instance.convert_pricing_amount()

                        if form.cleaned_data.get('delivery_method') is None:
                            instance.delivery_method = None

                        if form.cleaned_data.get('specific_fuel') is None:
                            instance.specific_fuel = None

                        if form.cleaned_data.get('specific_hookup_method') is None:
                            instance.specific_hookup_method = None

                        instance.supplier_fuel_fee = new_fuel_fee_entry
                        instance.valid_from_date = valid_from

                        if self.source_doc_type == 'agreement':
                            instance.price_active = self.new_document.is_active
                            instance.source_agreement = self.new_document
                        else:
                            instance.price_active = True

                        instance.pk = None
                        instance.save()

                        for key, value in request.POST.items():
                            if f'quantity_band_start-additional-{count}-' in key and value != "":
                                instance.quantity_band_start = value
                                continue
                            if f'quantity_band_end-additional-{count}-' in key and value != "":
                                instance.quantity_band_end = value
                                continue
                            if f'weight_band_start-additional-{count}-' in key and value != "":
                                instance.weight_band_start = value
                                continue
                            if f'weight_band_end-additional-{count}-' in key and value != "":
                                instance.weight_band_end = value
                                continue
                            if f'amount-additional-{count}-' in key:
                                instance.pricing_native_amount = value

                                if parent_entry.supplier_exchange_rate is not None:
                                    instance.convert_pricing_amount()

                                if self.source_doc_type == 'agreement':
                                    entry.source_agreement = self.new_document

                                instance.pk = None
                                instance.save()

                # Attach validity period to saved rates
                for form in fuel_fee_rate_formset:
                    new_periods = []

                    for key, value in request.POST.items():
                        if f'{form.prefix}-valid_from_dow' in key and value != "":
                            row_index = int(re.search(r'\d+$', key).group()) if 'additional' in key else 0
                            row_suffix = f'-additional-{row_index}' if row_index > 0 else ''

                            is_local = bool(request.POST.get(f'{form.prefix}-is_local'))
                            from_dow = int(value)
                            to_dow = int(request.POST.get(f'{form.prefix}-valid_to_dow{row_suffix}'))
                            from_time = request.POST.get(f'{form.prefix}-valid_from_time{row_suffix}')
                            to_time = request.POST.get(f'{form.prefix}-valid_to_time{row_suffix}')
                            all_day = request.POST.get(f'{form.prefix}-valid_all_day{row_suffix}')

                            if all_day:
                                from_time = time(0, 0, 0)
                                to_time = time(23, 59, 59)
                            else:
                                from_time = datetime.strptime(from_time, '%H:%M').time()
                                to_time = datetime.strptime(to_time, '%H:%M').time().replace(second=59)

                            new_periods.append((from_dow, to_dow, from_time, to_time, is_local))

                    for rate in form.instance.supplier_fuel_fee.rates.all():
                        rate.update_validity_periods(new_periods)

                if request.session.get(f'{self.source_doc_type}-{old_document.pk}-associated_fees_data'):
                    del request.session[f'{self.source_doc_type}-{old_document.pk}-associated_fees_data']

                request.session[f'{self.source_doc_type}-{self.session_doc_pk}-associated-fee-saved'] = True

                messages.success(request, 'Associated Fees saved successfully')

                return HttpResponseRedirect(self.return_url)
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'supplier_defined_tax_saved': request.session.get(f'{self.source_doc_type}-{self.session_doc_pk}-supplier-defined-taxes-saved', None),
                'document': old_document,
                'new_document': new_document,
                'document_type': self.source_doc_type,
                'fuel_fee_rate_formset': fuel_fee_rate_formset,
                'update_date_form': update_date_form,
            })
