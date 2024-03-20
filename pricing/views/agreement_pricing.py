import copy
from datetime import date, timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.http.response import JsonResponse
from django.db.models import Case, CharField, Exists, F, OuterRef, Q, Value, When
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalReadView, BSModalDeleteView
from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button
from core.utils.custom_query_expressions import CommaSeparatedDecimal, CommaSeparatedDecimalOrInteger
from core.utils.uom import get_uom_conversion_rate
from pricing.forms import FuelAgreementPricingFormulaFormset, \
    NewFuelAgreementPricingFormulaFormset, FuelAgreementPricingDiscountFormset, NewFuelAgreementPricingDiscountFormset
from pricing.models import FuelAgreementPricingFormula, FuelAgreementPricingManual, FuelIndexDetails, FuelType, \
    PricingUnit, SupplierFuelFee, SupplierFuelFeeRate, TaxRuleException
from pricing.utils.session import serialize_request_data
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin


###################
# FORMULA PRICING
###################

class AgreementFormulaPricingAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingFormula
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    agreement = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.agreement = get_object_or_404(FuelAgreement, pk=self.kwargs['pk'])

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': FuelAgreementPricingFormula.objects.get(id=pk),
            'table_name': 'formula_pricing',
            'table_url': reverse_lazy('admin:agreement_formula_pricing_sublist_ajax', kwargs={
                'agreement_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_details().with_index_pricing_status(self.agreement.supplier_id).filter(
            agreement_id=self.kwargs['pk'],
            parent_entry=None
        )

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'icao_iata', 'title': 'Airport/Location', 'visible': True,
         'className': 'url_source_col single_cell_link'},
        {'name': 'fuel', 'title': 'Fuel Type', 'foreign_field': 'fuel__name', 'visible': True, },
        {'name': 'destination_type', 'title': 'Destination', 'foreign_field': 'destination_type__name',
         'visible': True, },
        {'name': 'flight_type', 'title': 'Flight Type(s)', 'foreign_field': 'flight_type__name', 'visible': True, },
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'delivery_methods', 'title': 'Delivery Method(s)', 'm2m_foreign_field': 'delivery_methods__name',
         'visible': True,},
        {'name': 'specific_client', 'title': 'Specific Client', 'visible': True, 'className': 'text-wrap',
         'defaultContent': '--'},
        {'name': 'index', 'title': 'Index', 'className': 'text-wrap url_source_col single_cell_link', },
        {'name': 'differential', 'title': 'Differential', 'visible': True, 'sort_field': 'differential_value',
         'width': '140px'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, },
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'differential' in orders:
            if 'ASC' in str(params['orders'][0]):
                return qs.order_by('differential_pricing_unit__description_short', 'differential_value')
            else:
                return qs.order_by('-differential_pricing_unit__description_short', '-differential_value')
        else:
            return qs.order_by(*[order.get_order_mode() for order in params['orders']])

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                if column_link.name == 'operated_as':
                    if column_link.search_value == '0':
                        qs = qs.filter(applies_to_commercial=True)
                    elif column_link.search_value == '1':
                        qs = qs.filter(applies_to_private=True)
                    elif column_link.search_value == '2':
                        qs = qs.filter(applies_to_commercial=True, applies_to_private=True)
                elif column_link.name == 'differential':
                    search_value = column_link.search_value
                    if 'quantity band applies'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(band_uom=None))
                    else:
                        qs = qs.filter(Q(band_uom=None),
                                       Q(differential__icontains=search_value)
                                       ).distinct()
                elif column_link.name == 'delivery_methods':
                    search_value = column_link.search_value
                    if 'all'.startswith(search_value.lower()):
                        qs = qs.filter(Q(delivery_methods=None))
                    else:
                        qs = qs.filter(Q(delivery_methods__name__icontains=search_value))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def customize_row(self, row, obj):
        related_entries = FuelAgreementPricingFormula.objects.filter(parent_entry=obj.pk)

        if not row['delivery_methods']:
            row['delivery_methods'] = 'All'

        if related_entries.exists() or obj.band_uom:
            add_class = 'has_children'
            row['differential'] = f'Quantity Band Applies'
            view_btn = ''
        else:
            row['differential'] = obj.get_differential_datatable_str()
            add_class = ''
            view_btn = get_datatable_actions_button(
                button_text='',
                button_url=reverse_lazy('admin:agreement_formula_pricing_details',
                                        kwargs={'pk': obj.pk}),
                button_class='fa-eye',
                button_active=self.request.user.has_perm('pricing.p_view'),
                button_modal=True,
                modal_validation=True,
                button_modal_size="#modal-xl")

        edit_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy('admin:agreement_formula_pricing_edit',
                                    kwargs={'pk': obj.pk,
                                            'agreement_pk': self.kwargs['pk']}),
            button_class='fa-edit',
            button_active=self.request.user.has_perm('pricing.p_update'))

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy('admin:agreement_formula_pricing_delete',
                                                                          kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('pricing.p_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn

        row['icao_iata'] = f'<span class="{add_class}"' \
                           f'data-url="{obj.location.get_absolute_url()}">{obj.icao_iata}</span>'

        row['index'] = f'<span data-url="{obj.pricing_index.fuel_index.get_absolute_url()}">'\
                       f'{row["index"]}{obj.pricing_index_status_badge}</span>'


class AgreementFormulaPricingSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingFormula
    search_values_separator = '+'
    initial_order = [['band_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = FuelAgreementPricingFormula.objects.with_details().filter(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingFormula.objects.with_details().filter(
            parent_entry=self.kwargs['pk'])

        qs = parent_entry.union(related_entries).order_by('band_start')

        # Not sure if it impacts performance too much, but I'm only disabling it for the subtable
        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_start', 'title': 'Bands', 'placeholder': True, 'width': '213px'},
        {'name': 'differential', 'title': 'Differential', },
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_6', 'title': 'Bands', 'placeholder': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '30px'},
    ]

    def customize_row(self, row, obj):
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        row['band_start'] = f'{obj.band_uom}: {int(obj.band_start)} - {int(obj.band_end)}'
        row['differential'] = obj.get_differential_datatable_str()

        view_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy('admin:agreement_formula_pricing_details',
                                                                        kwargs={'pk': obj.pk}),
                                                button_class='fa-eye',
                                                button_active=self.request.user.has_perm('pricing.p_view'),
                                                button_modal=True,
                                                modal_validation=True,
                                                button_modal_size="#modal-xl")

        row['actions'] = view_btn

        return


class AgreementFormulaPricingDetailsView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'agreement_pricing_details_modal.html'
    model = FuelAgreementPricingFormula
    context_object_name = 'pricing'
    permission_required = ['pricing.p_view']

    def get_object(self):
        return FuelAgreementPricingFormula.objects.with_details().get(pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['pricing_type'] = 'formula'
        obj = self.get_object()
        context['fuel_fees'] = obj.relevant_fuel_fees
        context['taxes'] = obj.relevant_taxes

        metacontext = {
            'title': f'Location Pricing Details - {self.object.location.airport_details.icao_iata}',
            'icon': 'fa-eye',
        }

        context['metacontext'] = metacontext

        return context


class AgreementFormulaPricingCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'agreement_pricing_formula_form_page.html'
    permission_required = ['pricing.p_create']
    metacontext = {
        'mode': 'create',
        'title': 'Create Formula Pricing',
        'title_class': 'create',
        'default_volume_conversion_ratio_url': reverse_lazy('admin:default_volume_conversion_ratio'),
    }

    def get(self, request, *args, **kwargs):
        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])

        new_pricing_formset = NewFuelAgreementPricingFormulaFormset(form_kwargs={'agreement': agreement},
                                                                    agreement=agreement, context='Create',
                                                                    prefix='new-pricing')

        existing_fuel_pricing_entries = FuelAgreementPricingFormula.objects.filter(
            agreement=agreement)
        new_agreement = False

        if request.session.get(f'agreement-{agreement.pk}') and not existing_fuel_pricing_entries.exists():
            new_agreement = True

        return self.render_to_response({
            'doc_is_new': new_agreement,
            'agreement': agreement,
            'fuel_pricing_formset': new_pricing_formset,
            'metacontext': self.metacontext,
        })

    def post(self, request, *args, **kwargs):
        expected_forms = int(request.POST.get('new-pricing-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])

        new_pricing_formset = NewFuelAgreementPricingFormulaFormset(request.POST,
                                                                    form_kwargs={'agreement': agreement},
                                                                    agreement=agreement,
                                                                    extra_fields=extra_fields, context='Create',
                                                                    prefix='new-pricing')

        if all([
            new_pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                # Save new fuel pricing
                for count, form in enumerate(new_pricing_formset):
                    instance = form.save(commit=False)
                    if form.has_changed() and not form.cleaned_data.get('DELETE'):
                        instance.agreement = agreement
                        instance.price_active = agreement.is_active
                        instance.updated_by = request.user.person

                        # If we have extra, then we are not even going to care about the main differential_value
                        if extra_fields[count] != 0:
                            is_first_instance = True

                            for key, value in request.POST.items():
                                if f'-{count}-band_start' in key and value != "":
                                    instance.band_start = value
                                    continue
                                if f'-{count}-band_end' in key and value != "":
                                    instance.band_end = value
                                    continue
                                if f'-{count}-band_differential_value' in key:
                                    instance.differential_value = value

                                    if not is_first_instance:
                                        instance.parent_entry = parent_entry
                                        instance.save()
                                    else:
                                        instance.parent_entry = None
                                        is_first_instance = False
                                        instance.save()
                                        import copy
                                        parent_entry = copy.deepcopy(instance)

                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.pk = None

                        else:
                            band_pricing = request.POST.get(f'new-pricing-{count}-band_differential_value')

                            if band_pricing:
                                instance.differential_value = band_pricing

                            instance.save()
                            instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                        # Update included taxes (must be done after new instance is saved)
                        main_instance = instance if instance.pk else parent_entry
                        inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                        cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                        main_instance.inclusive_taxes = inclusive_taxes, cascade_to_fees

                messages.success(request, 'Fuel Pricing created successfully')

                if request.session.get(f'agreement-{agreement.id}'):
                    return HttpResponseRedirect(
                        reverse_lazy('admin:agreement_supplier_fee_create',
                                     kwargs={'agreement_pk': agreement.id}))
                else:
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                             kwargs={'pk': agreement.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            existing_fuel_pricing_entries = FuelAgreementPricingFormula.objects.filter(
                agreement=agreement)

            new_agreement = False
            if request.session.get(f'agreement-{agreement.id}') and not existing_fuel_pricing_entries.exists():
                new_agreement = True

            return self.render_to_response({
                'doc_is_new': new_agreement,
                'agreement': agreement,
                'fuel_pricing_formset': new_pricing_formset,
                'metacontext': self.metacontext,
            })


class AgreementFormulaPricingEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'agreement_pricing_formula_form_page.html'
    permission_required = ['pricing.p_update']
    metacontext = {
        'mode': 'edit',
        'title': 'Edit Formula Pricing',
        'title_class': 'edit',
        'default_volume_conversion_ratio_url': reverse_lazy('admin:default_volume_conversion_ratio'),
    }

    def get(self, request, *args, **kwargs):
        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        self.metacontext['back_url'] = reverse_lazy('admin:fuel_agreement', kwargs={'pk': agreement.pk})

        entry = FuelAgreementPricingFormula.objects.get(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingFormula.objects.filter(parent_entry=self.kwargs['pk'])

        pricing_formset = FuelAgreementPricingFormulaFormset(form_kwargs={'context': 'Edit', 'entry': entry},
                                                             agreement=agreement, prefix='new-pricing', context='Edit',
                                                             entry=entry, related_entries=related_entries)

        return self.render_to_response({
            'agreement': agreement,
            'fuel_pricing_formset': pricing_formset,
            'metacontext': self.metacontext,
        })

    def post(self, request, *args, **kwargs):
        extra_fields = {0: 0}
        for key in request.POST:
            if f'band_start-additional' in key:
                extra_fields[0] += 1

        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        self.metacontext['back_url'] = reverse_lazy('admin:fuel_agreement', kwargs={'pk': agreement.pk})

        entry = FuelAgreementPricingFormula.objects.get(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingFormula.objects.filter(parent_entry=self.kwargs['pk']) \
            .order_by('band_start')

        pricing_formset = FuelAgreementPricingFormulaFormset(
            request.POST,
            form_kwargs={'agreement': agreement, 'context': 'Edit', 'entry': entry},
            agreement=agreement, context="Edit", entry=entry, related_entries=related_entries,
            extra_fields=extra_fields, prefix='new-pricing')

        if all([
            pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                has_new_bands = False
                location = entry.location

                for field in request.POST:
                    if 'additional' in field:
                        has_new_bands = True

                for count, form in enumerate(pricing_formset):
                    instance = form.save(commit=False)
                    instance.updated_by = request.user.person
                    instance.location = location
                    band_pricing = request.POST.get(f'new-pricing-{count}-band_differential_value')
                    existing_entry = 0

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    # Update included taxes
                    inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                    cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                    instance.inclusive_taxes = inclusive_taxes, cascade_to_fees
                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                    if band_pricing:
                        instance.differential_value = band_pricing
                        import copy
                        parent_entry = copy.deepcopy(instance)

                    instance.save()

                    # Save new bands as new instances
                    if has_new_bands:
                        instance.pk = None

                        for key, value in request.POST.items():
                            if f'band_start-additional' in key and value != "":
                                instance.band_start = value
                                continue
                            if f'band_end-additional' in key and value != "":
                                instance.band_end = value
                                continue
                            if f'value-additional' in key:
                                instance.differential_value = value
                                instance.parent_entry = parent_entry

                                if existing_entry < related_entries.count():
                                    instance.pk = related_entries[existing_entry].pk
                                    instance.save()
                                    existing_entry += 1
                                else:
                                    instance.save()

                                instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                instance.pk = None

                    # Delete the remaining
                    while existing_entry < related_entries.count():
                        related_entries[existing_entry].delete()
                        existing_entry += 1

                messages.success(request, 'Fuel Pricing updated successfully')

                # Redirect to agreement page
                return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                         kwargs={'pk': agreement.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'agreement': agreement,
                'fuel_pricing_formset': pricing_formset,
                'metacontext': self.metacontext,
            })


class AgreementFormulaPricingDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = FuelAgreementPricingFormula
    form_class = ConfirmationForm
    success_message = 'Pricing entry has been archived'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Archive Formula Fuel Pricing Entry',
            'text': f'Are you sure you want to archive this fuel pricing entry?',
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.archive(self.request.user.person)
        return HttpResponseRedirect(success_url)


class DefaultVolumeConversionRateAjaxView(AdminPermissionsMixin, View):
    permission_required = ['pricing.p_view']

    def post(self, request, *args, **kwargs):
        fuel_pk = request.POST['fuel_pk']
        unit_pk = request.POST['unit_pk']
        index_details_pk = request.POST['index_details_pk']

        fuel = get_object_or_404(FuelType, pk=fuel_pk)
        unit = get_object_or_404(PricingUnit, pk=unit_pk)
        index = get_object_or_404(FuelIndexDetails, pk=index_details_pk)

        try:
            conversion_rate = get_uom_conversion_rate(
                index.pricing_unit.uom, unit.uom, fuel)
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)

            return JsonResponse({
                'success': 'false',
                'exception': str(e),
            })

        return JsonResponse({
            'success': 'true',
            'from': index.pricing_unit.uom.description,
            'to': unit.uom.description,
            'fuel': fuel.name,
            'rate': '{:f}'.format(round(conversion_rate, 5).normalize()),
        })


###################
# DISCOUNT PRICING
###################

class AgreementDiscountPricingAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingManual
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': FuelAgreementPricingManual.objects.get(id=pk),
            'table_name': 'discount_pricing',
            'table_url': reverse_lazy('admin:agreement_discount_pricing_sublist_ajax', kwargs={
                'agreement_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_details().filter(
            agreement_id=self.kwargs['pk'],
            parent_entry=None
        )

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'icao_iata', 'title': 'Airport/Location', 'visible': True,
         'className': 'url_source_col single_cell_link'},
        {'name': 'fuel', 'title': 'Fuel Type', 'foreign_field': 'fuel__name', 'visible': True, },
        {'name': 'destination_type', 'title': 'Destination', 'foreign_field': 'destination_type__name',
         'visible': True, },
        {'name': 'flight_type', 'title': 'Flight Type(s)', 'foreign_field': 'flight_type__name', 'visible': True, },
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'delivery_methods', 'title': 'Delivery Method(s)', 'm2m_foreign_field': 'delivery_methods__name',
         'visible': True,},
        {'name': 'specific_client', 'title': 'Specific Client', 'visible': True, 'className': 'text-wrap',
         'defaultContent': '--'},
        {'name': 'discount_amount', 'title': 'Discount<br>(Amount)', 'visible': True, 'searchable': True,
         'defaultContent': '--', 'width': '140px'},
        {'name': 'discount_percentage', 'title': 'Discount<br>(Percentage)', 'visible': True, 'searchable': True,
         'sort_field': 'pricing_discount_percentage', 'defaultContent': '--', 'width': '140px'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, },
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'discount_amount' in orders:
            if 'ASC' in str(params['orders'][0]):
                return qs.order_by('pricing_discount_unit', 'pricing_discount_amount')
            else:
                return qs.order_by('-pricing_discount_unit', '-pricing_discount_amount')
        else:
            return qs.order_by(*[order.get_order_mode() for order in params['orders']])

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                if column_link.name == 'operated_as':
                    if column_link.search_value == '0':
                        qs = qs.filter(applies_to_commercial=True)
                    elif column_link.search_value == '1':
                        qs = qs.filter(applies_to_private=True)
                    elif column_link.search_value == '2':
                        qs = qs.filter(applies_to_commercial=True, applies_to_private=True)
                elif column_link.name == 'discount_amount':
                    search_value = column_link.search_value
                    qs = qs.filter(Q(discount_amount__isnull=False))

                    if 'quantity band applies'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(band_uom=None))
                    else:
                        qs = qs.filter(Q(band_uom=None),
                                       Q(discount_amount__icontains=search_value)
                                       ).distinct()
                elif column_link.name == 'discount_percentage':
                    search_value = column_link.search_value
                    qs = qs.filter(Q(discount_percentage__isnull=False))

                    if 'quantity band applies'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(band_uom=None))
                    else:
                        qs = qs.filter(Q(band_uom=None),
                                       Q(discount_percentage__icontains=search_value)
                                       ).distinct()
                elif column_link.name == 'delivery_methods':
                    search_value = column_link.search_value
                    if 'all'.startswith(search_value.lower()):
                        qs = qs.filter(Q(delivery_methods=None))
                    else:
                        qs = qs.filter(Q(delivery_methods__name__icontains=search_value))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def customize_row(self, row, obj):
        related_entries = FuelAgreementPricingManual.objects.filter(parent_entry=obj.pk)

        if not row['delivery_methods']:
            row['delivery_methods'] = 'All'

        if related_entries.exists() or obj.band_uom:
            add_class = 'has_children'

            if obj.discount_amount:
                row['discount_amount'] = f'Quantity Band Applies'
            else:
                row['discount_percentage'] = f'Quantity Band Applies'

            view_btn = ''
        else:
            add_class = ''

            if obj.discount_amount:
                row['discount_amount'] = obj.get_discount_datatable_str()
            else:
                row['discount_percentage'] = obj.get_discount_datatable_str()

            view_btn = get_datatable_actions_button(button_text='',
                                                    button_url=reverse_lazy('admin:agreement_discount_pricing_details',
                                                                            kwargs={'pk': obj.pk}),
                                                    button_class='fa-eye',
                                                    button_active=self.request.user.has_perm('pricing.p_view'),
                                                    button_modal=True,
                                                    modal_validation=True,
                                                    button_modal_size="#modal-xl")

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy('admin:agreement_discount_pricing_edit',
                                                                        kwargs={'pk': obj.pk,
                                                                                'agreement_pk': self.kwargs['pk']}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm('pricing.p_update'))

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy('admin:agreement_discount_pricing_delete',
                                                                          kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('pricing.p_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        row['icao_iata'] = f'<span class="{add_class}"' \
                           f'data-url="{obj.location.get_absolute_url()}">{obj.icao_iata}</span>'


class AgreementDiscountPricingSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingManual
    search_values_separator = '+'
    initial_order = [['band_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = FuelAgreementPricingManual.objects.with_details().filter(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingManual.objects.with_details().filter(
            parent_entry=self.kwargs['pk'])

        qs = parent_entry.union(related_entries).order_by('band_start')

        # Not sure if it impacts performance too much, but I'm only disabling it for the subtable
        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_start', 'title': 'Bands', 'placeholder': True, 'width': '213px'},
        {'name': 'discount', 'title': 'Discount', },
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True, },
        {'name': 'dummy_6', 'title': 'Bands', 'placeholder': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '30px'},
    ]

    def customize_row(self, row, obj):
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        row['band_start'] = f'{obj.band_uom}: {int(obj.band_start)} - {int(obj.band_end)}'
        row['discount'] = obj.get_discount_datatable_str() or '--'

        view_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy('admin:agreement_discount_pricing_details',
                                                                        kwargs={'pk': obj.pk}),
                                                button_class='fa-eye',
                                                button_active=self.request.user.has_perm('pricing.p_view'),
                                                button_modal=True,
                                                modal_validation=True,
                                                button_modal_size="#modal-xl")

        row['actions'] = view_btn

        return


class AgreementDiscountPricingDetailsView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'agreement_pricing_details_modal.html'
    model = FuelAgreementPricingManual
    context_object_name = 'pricing'
    permission_required = ['pricing.p_view']

    def get_object(self):
        return FuelAgreementPricingManual.objects.with_details().get(pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['pricing_type'] = 'discount'
        obj = self.get_object()
        context['fuel_fees'] = obj.relevant_fuel_fees
        context['taxes'] = obj.relevant_taxes

        metacontext = {
            'title': f'Location Pricing Details - {self.object.location.airport_details.icao_iata}',
            'icon': 'fa-eye',
        }

        context['metacontext'] = metacontext

        return context


class AgreementDiscountPricingCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'agreement_pricing_discount_form_page.html'
    permission_required = ['pricing.p_create']
    metacontext = {
        'mode': 'create',
        'title': 'Create Discount Pricing',
        'title_class': 'create',
    }

    def get(self, request, *args, **kwargs):
        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])

        new_pricing_formset = NewFuelAgreementPricingDiscountFormset(form_kwargs={'agreement': agreement},
                                                                     agreement=agreement, context='Create',
                                                                     prefix='new-pricing')

        existing_fuel_pricing_entries = FuelAgreementPricingManual.objects.filter(
            agreement=agreement)
        new_agreement = False

        if request.session.get(f'agreement-{agreement.pk}') and not existing_fuel_pricing_entries.exists():
            new_agreement = True

        return self.render_to_response({
            'doc_is_new': new_agreement,
            'agreement': agreement,
            'fuel_pricing_formset': new_pricing_formset,
            'metacontext': self.metacontext,
        })

    def post(self, request, *args, **kwargs):
        expected_forms = int(request.POST.get('new-pricing-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])

        new_pricing_formset = NewFuelAgreementPricingDiscountFormset(request.POST,
                                                                     form_kwargs={'agreement': agreement},
                                                                     agreement=agreement, extra_fields=extra_fields,
                                                                     context='Create', prefix='new-pricing')

        if all([
            new_pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                # Save new fuel pricing
                for count, form in enumerate(new_pricing_formset):
                    instance = form.save(commit=False)
                    is_percentage = request.POST.get(f'new-pricing-{count}-is_percentage')

                    if form.has_changed() and not form.cleaned_data.get('DELETE'):
                        instance.agreement = agreement
                        instance.price_active = agreement.is_active
                        instance.updated_by = request.user.person

                        if is_percentage:
                            instance.pricing_discount_unit = None

                        # If we have extra, then we are not even going to care about the main discount value
                        if extra_fields[count] != 0:
                            is_first_instance = True

                            for key, value in request.POST.items():
                                if f'-{count}-band_start' in key and value != "":
                                    instance.band_start = value
                                    continue
                                if f'-{count}-band_end' in key and value != "":
                                    instance.band_end = value
                                    continue

                                if is_percentage:
                                    if f'-{count}-band_discount_percentage' in key:
                                        instance.pricing_discount_percentage = value
                                        instance.pricing_discount_amount = None
                                        instance.pricing_discount_unit = None

                                        if not is_first_instance:
                                            instance.parent_entry = parent_entry
                                            instance.save()
                                        else:
                                            instance.parent_entry = None
                                            is_first_instance = False
                                            instance.save()
                                            import copy
                                            parent_entry = copy.deepcopy(instance)

                                        instance.pk = None
                                else:
                                    if f'-{count}-band_discount_amount' in key:
                                        instance.pricing_discount_amount = value
                                        instance.pricing_discount_percentage = None

                                        if not is_first_instance:
                                            instance.parent_entry = parent_entry
                                            instance.save()
                                        else:
                                            instance.parent_entry = None
                                            is_first_instance = False
                                            instance.save()
                                            import copy
                                            parent_entry = copy.deepcopy(instance)

                                        instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                        instance.pk = None

                        else:
                            if is_percentage:
                                band_pricing = request.POST.get(f'new-pricing-{count}-band_discount_percentage')

                                if band_pricing:
                                    instance.pricing_discount_percentage = band_pricing
                                    instance.pricing_discount_amount = None
                            else:
                                band_pricing = request.POST.get(f'new-pricing-{count}-band_discount_amount')

                                if band_pricing:
                                    instance.pricing_discount_amount = band_pricing
                                    instance.pricing_discount_percentage = None

                            instance.save()
                            instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                        # Update included taxes and delivery methods for main entry (M2M relations)
                        main_instance = instance if instance.pk else parent_entry
                        inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                        cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                        main_instance.inclusive_taxes = inclusive_taxes, cascade_to_fees

                messages.success(request, 'Fuel Pricing created successfully')

                if request.session.get(f'agreement-{agreement.id}'):
                    return HttpResponseRedirect(
                        reverse_lazy('admin:agreement_supplier_fee_create',
                                     kwargs={'agreement_pk': agreement.id}))
                else:
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                             kwargs={'pk': agreement.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            existing_fuel_pricing_entries = FuelAgreementPricingManual.objects.filter(
                agreement=agreement)

            new_agreement = False
            if request.session.get(f'agreement-{agreement.id}') and not existing_fuel_pricing_entries.exists():
                new_agreement = True

            return self.render_to_response({
                'doc_is_new': new_agreement,
                'agreement': agreement,
                'fuel_pricing_formset': new_pricing_formset,
                'metacontext': self.metacontext,
            })


class AgreementDiscountPricingEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'agreement_pricing_discount_form_page.html'
    permission_required = ['pricing.p_update']
    metacontext = {
        'mode': 'edit',
        'title': 'Edit Discount Pricing',
        'title_class': 'edit',
    }

    def get(self, request, *args, **kwargs):
        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        self.metacontext['back_url'] = reverse_lazy('admin:fuel_agreement', kwargs={'pk': agreement.pk})

        entry = FuelAgreementPricingManual.objects.get(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingManual.objects.filter(parent_entry=self.kwargs['pk'])

        pricing_formset = FuelAgreementPricingDiscountFormset(form_kwargs={'context': 'Edit', 'entry': entry},
                                                              agreement=agreement, prefix='new-pricing', context='Edit',
                                                              entry=entry, related_entries=related_entries)

        return self.render_to_response({
            'agreement': agreement,
            'fuel_pricing_formset': pricing_formset,
            'metacontext': self.metacontext,
        })

    def post(self, request, *args, **kwargs):
        extra_fields = {0: 0}
        for key in request.POST:
            if f'band_start-additional' in key:
                extra_fields[0] += 1

        agreement = FuelAgreement.objects.get(pk=self.kwargs['agreement_pk'])
        self.metacontext['back_url'] = reverse_lazy('admin:fuel_agreement', kwargs={'pk': agreement.pk})

        entry = FuelAgreementPricingManual.objects.get(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingManual.objects.filter(parent_entry=self.kwargs['pk']) \
            .order_by('band_start')

        pricing_formset = FuelAgreementPricingDiscountFormset(
            request.POST,
            form_kwargs={'agreement': agreement, 'context': 'Edit', 'entry': entry},
            agreement=agreement, context="Edit", entry=entry, extra_fields=extra_fields,
            related_entries=related_entries, prefix='new-pricing')

        if all([
            pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                has_new_bands = False
                location = entry.location

                for field in request.POST:
                    if 'additional' in field:
                        has_new_bands = True

                for count, form in enumerate(pricing_formset):
                    instance = form.save(commit=False)
                    instance.updated_by = request.user.person
                    instance.location = location
                    is_percentage = request.POST.get(f'new-pricing-{count}-is_percentage')
                    existing_entry = 0

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    # Update included taxes
                    inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                    cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                    instance.inclusive_taxes = inclusive_taxes, cascade_to_fees
                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                    if is_percentage:
                        instance.pricing_discount_unit = None
                        instance.pricing_discount_amount = None
                        band_pricing = request.POST.get(f'new-pricing-{count}-band_discount_percentage')

                        if band_pricing:
                            instance.pricing_discount_percentage = band_pricing
                            import copy
                            parent_entry = copy.deepcopy(instance)

                        instance.save()
                    else:
                        instance.pricing_discount_percentage = None
                        band_pricing = request.POST.get(f'new-pricing-{count}-band_discount_amount')

                        if band_pricing:
                            instance.pricing_discount_amount = band_pricing
                            import copy
                            parent_entry = copy.deepcopy(instance)

                        instance.save()

                    # Save new bands as new instances
                    if has_new_bands:
                        instance.pk = None

                        for key, value in request.POST.items():
                            if f'band_start-additional' in key and value != "":
                                instance.band_start = value
                                continue
                            if f'band_end-additional' in key and value != "":
                                instance.band_end = value
                                continue

                            if form.cleaned_data.get('is_percentage'):
                                if f'percentage-additional' in key:
                                    instance.pricing_discount_percentage = value
                                    instance.parent_entry = parent_entry

                                    if existing_entry < related_entries.count():
                                        instance.pk = related_entries[existing_entry].pk
                                        instance.save()
                                        existing_entry += 1
                                    else:
                                        instance.save()

                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.pk = None
                            else:
                                if f'amount-additional' in key:
                                    instance.pricing_discount_amount = value
                                    instance.parent_entry = parent_entry

                                    if existing_entry < related_entries.count():
                                        instance.pk = related_entries[existing_entry].pk
                                        instance.save()
                                        existing_entry += 1
                                    else:
                                        instance.save()

                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.pk = None

                    # Delete the remaining
                    while existing_entry < related_entries.count():
                        related_entries[existing_entry].delete()
                        existing_entry += 1

                messages.success(request, 'Fuel Pricing updated successfully')

                # Redirect to agreement page
                return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement',
                                                         kwargs={'pk': agreement.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'agreement': agreement,
                'fuel_pricing_formset': pricing_formset,
                'metacontext': self.metacontext,
            })


class AgreementDiscountPricingDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = FuelAgreementPricingManual
    form_class = ConfirmationForm
    success_message = 'Pricing entry has been archived'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Archive Discount Fuel Pricing Entry',
            'text': f'Are you sure you want to archive this fuel pricing entry?',
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.archive(self.request.user.person)
        return HttpResponseRedirect(success_url)


###################
# ASSOCIATED FEES
###################

class AgreementPricingAssociatedFeesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFee
    search_values_separator = '+'
    initial_order = [['local_name', "asc"]]
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': self.model.objects.get(id=pk),
            'table_name': 'associated_fees',
            'table_url': reverse_lazy('admin:agreement_associated_fees_sublist_ajax', kwargs={
                'agreement_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_rate_details().filter(
            rates__source_agreement_id=self.kwargs['pk'],
        )

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
         'orderable': False, 'width': '10px'},
        {'name': 'local_name', 'title': 'Name', },
        {'name': 'icao_iata', 'title': 'Location', 'placeholder': True},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'fuel_fee_category__name'},
        {'name': 'specific_fuel', 'title': 'Fuel', },
        {'name': 'destination_type', 'title': 'Destination Type', },
        {'name': 'flight_type', 'title': 'Flight Type'},
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'unit_rate_string', 'title': 'Fee', 'orderable': True, 'width': '150px'},
        {'name': 'actions', 'title': '',
         'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_value = column_link.search_value

                if column_link.name == 'operated_as':
                    if column_link.search_value == '0':
                        qs = qs.filter(rates__applies_to_commercial=True)
                    elif column_link.search_value == '1':
                        qs = qs.filter(rates__applies_to_private=True)
                    elif column_link.search_value == '2':
                        qs = qs.filter(rates__applies_to_commercial=True, rates__applies_to_private=True)
                elif column_link.name == "unit_rate_string":
                    if 'multiple rates apply'.startswith(search_value.lower()):
                        qs = qs.filter(rate_count__gt=1)
                    elif 'weight band applies'.startswith(search_value.lower()):
                        qs = qs.filter(has_weight_band=True)
                    elif 'quantity band applies'.startswith(search_value.lower()):
                        qs = qs.filter(has_quantity_band=True)
                    elif 'bands apply'.startswith(search_value.lower()):
                        qs = qs.filter(~Q(rates__quantity_band_uom=None) | ~Q(rates__weight_band=None))
                    else:
                        qs = qs.filter(
                            ~Exists(qs.filter(
                                Q(pk=OuterRef('pk')) &
                                (Q(rate_count__gt=1) | Q(has_weight_band=True) | Q(has_quantity_band=True)))) &
                            (Exists(qs.filter(
                                Q(pk=OuterRef('pk')) &
                                (Q(rates__pricing_native_unit__description_short__icontains=search_value) |
                                 Q(rates__pricing_converted_unit__description_short__icontains=search_value)))))
                        )
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs.distinct()

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'unit_rate_string' in orders:
            if 'ASC' in str(params['orders'][0]):
                return qs.order_by('rate_count', 'has_weight_band', 'has_quantity_band')
            else:
                return qs.order_by('-rate_count', '-has_weight_band', '-has_quantity_band')
        else:
            return qs.order_by(*[order.get_order_mode() for order in params['orders']])

    def customize_row(self, row, obj):
        entries = obj.rates

        if entries.count() == 0:
            return

        if entries.count() > 1 or obj.has_weight_band or obj.has_quantity_band:
            add_class = 'has_children'
        else:
            add_class = ''

        row['local_name'] = f'<span class="{add_class}"\>{obj.local_name}</span>'
        formatted_flight_type = obj.flight_type.replace('s Only', 's').replace(' Only', 's')
        row['flight_type'] = formatted_flight_type

        if obj.applies_to_commercial and obj.applies_to_private:
            row['operated_as'] = 'Commercial, Private'
        else:
            row['operated_as'] = 'Private' if obj.applies_to_private else 'Commercial'

        view_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:agreement_supplier_fee_details',
                                                    kwargs={'pk': obj.pk, 'agreement_pk': self.kwargs['pk']}),
                                                button_class='fa-eye',
                                                button_active=self.request.user.has_perm(
                                                    'pricing.p_view'),
                                                button_modal=False,
                                                modal_validation=True)

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:agreement_supplier_fee_edit',
                                                    kwargs={'pk': obj.pk, 'agreement_pk': self.kwargs['pk']}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'pricing.p_update'))

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:agreement_supplier_fee_archive',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'pricing.p_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        return


# Fuel Fee Subtable
class AgreementPricingAssociatedFeesSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFeeRate
    search_values_separator = '+'
    initial_order = [['quantity_band_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        qs = self.model.objects.with_details().filter(supplier_fuel_fee__pk=self.kwargs['pk'])

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'quantity_band_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'weight_band_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'specific_fuel', 'title': 'Fuel', 'lookup_field': '__name__icontains',
         'defaultContent': '--'},
        {'name': 'destination_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'pricing_amount', 'title': 'Native Pricing', 'placeholder': True},
        {'name': 'dummy_actions', 'title': '', 'placeholder': True, },
    ]

    def customize_row(self, row, obj):

        for name in row:
            if 'dummy' in name:
                row[name] = ''

        if obj.quantity_band_start is not None:
            row['quantity_band_start'] = f'{obj.quantity_band_uom}:<br>' \
                                         f'{int(obj.quantity_band_start)} - {int(obj.quantity_band_end)}'
        else:
            row['quantity_band_start'] = ''

        if obj.weight_band_start is not None:
            row['weight_band_start'] = f'{obj.weight_band}:<br>' \
                                       f'{int(obj.weight_band_start)} - {int(obj.weight_band_end)}'
        else:
            row['weight_band_start'] = ''

        row['pricing_amount'] = obj.unit_rate_string_inc_conversion_short

        # Wrap all cell contents in an additional div to fix widths
        for col in row:
            row[col] = f'<div>{row[col]}</div>'

        return


class AgreementPricingSupersedeView(AdminPermissionsMixin, TemplateView):
    template_name = 'agreement_pricing_supersede_form_page.html'
    permission_required = ['pricing.p_create']
    metacontext = {
        'default_volume_conversion_ratio_url': reverse_lazy('admin:default_volume_conversion_ratio'),
    }

    def get(self, request, *args, **kwargs):
        new_agreement = FuelAgreement.objects.get(pk=self.kwargs.get('pk', None))
        old_agreement = new_agreement.superseded_agreement

        if new_agreement.superseded_by_id is not None:
            messages.error(request, 'The document has already been superseded')
            return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement'))

        related_entries_formula = FuelAgreementPricingFormula.objects.filter(
            Q(agreement=old_agreement), Q(deleted_at__isnull=False),
            ~Q(parent_entry=None)).order_by('band_start')

        related_entries_discount = FuelAgreementPricingManual.objects.filter(
            Q(agreement=old_agreement), Q(deleted_at__isnull=False),
            ~Q(parent_entry=None)).order_by('band_start')

        pricing_formset_formula = FuelAgreementPricingFormulaFormset(
            form_kwargs={'agreement': new_agreement, 'context': 'Supersede'},
            agreement=new_agreement, old_agreement=old_agreement, context='Supersede',
            prefix='existing-formula-pricing'
        )

        pricing_formset_discount = FuelAgreementPricingDiscountFormset(
            form_kwargs={'agreement': new_agreement, 'context': 'Supersede'},
            agreement=new_agreement, old_agreement=old_agreement, context='Supersede',
            prefix='existing-discount-pricing'
        )

        if f'{new_agreement.id}-agreement_pricing_list_data' in request.session:
            session_data = request.session[f'{new_agreement.id}-agreement_pricing_list_data']

            # Formula pricing
            form_numbers = session_data.get('existing-formula-pricing-TOTAL_FORMS')

            extra_fields = {i: 0 for i in range(int(form_numbers))}
            for form_number in extra_fields:
                for key in session_data:
                    if f'formula-pricing-{form_number}-band_start-additional' in key:
                        extra_fields[form_number] += 1

            pricing_formset_formula = FuelAgreementPricingFormulaFormset(
                data=session_data,
                form_kwargs={'agreement': new_agreement, 'context': 'Supersede'},
                agreement=new_agreement, old_agreement=old_agreement, context='Supersede',
                extra_fields=extra_fields, prefix='existing-formula-pricing')

            # Discount pricing
            form_numbers = session_data.get('existing-discount-pricing-TOTAL_FORMS')

            extra_fields = {i: 0 for i in range(int(form_numbers))}
            for form_number in extra_fields:
                for key in session_data:
                    if f'discount-pricing-{form_number}-band_start-additional' in key:
                        extra_fields[form_number] += 1

            pricing_formset_discount = FuelAgreementPricingDiscountFormset(
                data=session_data,
                form_kwargs={'agreement': new_agreement, 'context': 'Supersede'},
                agreement=new_agreement, old_agreement=old_agreement, context='Supersede',
                extra_fields=extra_fields, prefix='existing-discount-pricing')

        return self.render_to_response({
            'associated_fee_saved': request.session.get(f'agreement-{new_agreement.id}-associated-fee-saved', None),
            'supplier_defined_tax_saved': request.session.get(
                f'agreement-{new_agreement.id}-supplier-defined-taxes-saved', None),
            'document': new_agreement,
            'related_entries_formula': related_entries_formula,
            'related_entries_discount': related_entries_discount,
            'pricing_formset_formula': pricing_formset_formula,
            'pricing_formset_discount': pricing_formset_discount,
            'metacontext': self.metacontext,
        })

    def post(self, request, *args, **kwargs):
        new_agreement = FuelAgreement.objects.get(pk=self.kwargs.get('pk', None))
        old_agreement = new_agreement.superseded_agreement

        # Formula pricing
        related_entries_formula = FuelAgreementPricingFormula.objects.filter(
            Q(agreement=old_agreement), Q(deleted_at__isnull=False),
            ~Q(parent_entry=None)).order_by('band_start')

        form_numbers = request.POST.get('existing-formula-pricing-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        for form_number in extra_fields:
            for key in request.POST:
                if f'formula-pricing-{form_number}-band_start-additional' in key:
                    extra_fields[form_number] += 1

        pricing_formset_formula = FuelAgreementPricingFormulaFormset(
            request.POST, form_kwargs={'agreement': new_agreement,
                                       'context': 'Supersede'},
            agreement=new_agreement, old_agreement=old_agreement,
            context='Supersede', extra_fields=extra_fields,
            prefix='existing-formula-pricing'
        )

        # Discount pricing
        related_entries_discount = FuelAgreementPricingManual.objects.filter(
            Q(agreement=old_agreement), Q(deleted_at__isnull=False),
            ~Q(parent_entry=None)).order_by('band_start')

        form_numbers = request.POST.get('existing-discount-pricing-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        for form_number in extra_fields:
            for key in request.POST:
                if f'discount-pricing-{form_number}-band_start-additional' in key:
                    extra_fields[form_number] += 1

        pricing_formset_discount = FuelAgreementPricingDiscountFormset(
            request.POST, form_kwargs={'agreement': new_agreement,
                                       'context': 'Supersede'},
            agreement=new_agreement, old_agreement=old_agreement,
            context='Supersede', extra_fields=extra_fields,
            prefix='existing-discount-pricing'
        )

        if 'taxes' in request.POST['button-pressed']:
            request.session[f'{new_agreement.id}-agreement_pricing_list_data'] = serialize_request_data(request.POST)

            messages.info(request, 'Fuel Pricing form fields were saved')
            return HttpResponseRedirect(reverse_lazy('admin:agreement_supplier_tax_supersede',
                                                     kwargs={'pk': new_agreement.id}))

        elif 'associated-fees' in request.POST['button-pressed']:
            request.session[f'{new_agreement.id}-agreement_pricing_list_data'] = serialize_request_data(request.POST)

            messages.info(request, 'Fuel Pricing form fields were saved')
            return HttpResponseRedirect(reverse_lazy('admin:agreement_supplier_fees_supersede',
                                                     kwargs={'pk': new_agreement.id}))

        if all([
            pricing_formset_formula.is_valid(),
            pricing_formset_discount.is_valid(),
        ]):
            # Note: have to save(commit=False) to access deleted_objects
            pricing_formset_formula.save(commit=False)
            pricing_formset_discount.save(commit=False)

            # Save existing pricing as new
            for pricing_formset in [pricing_formset_formula, pricing_formset_discount]:
                pricing_type = 'formula-pricing' if 'formula' in pricing_formset.prefix else 'discount-pricing'
                pricing_class = FuelAgreementPricingFormula if 'formula' in pricing_formset.prefix \
                    else FuelAgreementPricingManual

                for count, form in enumerate(pricing_formset):
                    instance = form.save(commit=False)

                    if instance in pricing_formset.deleted_objects:
                        # Preserve deleted entry and its children
                        instance.refresh_from_db()
                        instance.save()
                    else:
                        if form.cleaned_data.get('specific_hookup_method') is None:
                            instance.specific_hookup_method = None

                        is_percentage = bool(form.cleaned_data.get('is_percentage', False))

                        # This is simpler then in Market Pricing's case, as pricing has no individual dates here
                        entry = pricing_class.objects.get(id=instance.id)
                        entry.save()

                        # Create new entries
                        if form.cleaned_data.get('specific_hookup_method') is None:
                            instance.specific_hookup_method = None

                        instance.id = None
                        instance.updated_by = request.user.person
                        instance.parent_entry = None
                        instance.agreement = new_agreement
                        instance.price_active = new_agreement.is_active

                        if is_percentage:
                            instance.pricing_discount_amount = None
                            instance.pricing_discount_unit = None
                        else:
                            instance.pricing_discount_percentage = None

                        instance.save()

                        # Update included taxes (must be done after new instance is saved)
                        instance.inclusive_taxes = \
                            form.cleaned_data.get('inclusive_taxes'), form.cleaned_data.get('cascade_to_fees')
                        instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                        parent_entry = copy.deepcopy(instance)
                        instance.id = None

                        extra_fields = False
                        for key, value in request.POST.items():
                            if f'additional-{count}-' in key:
                                extra_fields = True
                                break

                        if extra_fields:
                            for key, value in request.POST.items():
                                if f'{pricing_type}-{count}-band_start' in key and value != "":
                                    instance.band_start = value
                                    continue
                                if f'{pricing_type}-{count}-band_end' in key and value != "":
                                    instance.band_end = value
                                    continue
                                if f'{pricing_type}-{count}-band_differential_value' in key and 'old' not in key and value:
                                    instance.differential_value = value
                                    instance.parent_entry = parent_entry
                                    instance.save()
                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.id = None
                                    continue
                                if f'{pricing_type}-{count}-band_discount_amount' in key and 'old' not in key and not is_percentage:
                                    instance.pricing_discount_amount = value
                                    instance.parent_entry = parent_entry
                                    instance.save()
                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.id = None
                                    continue
                                if f'{pricing_type}-{count}-band_discount_percentage' in key and 'old' not in key and is_percentage:
                                    instance.pricing_discount_percentage = value
                                    instance.parent_entry = parent_entry
                                    instance.save()
                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.id = None
                                    continue

            if request.session.get(f'{new_agreement.id}-agreement_pricing_list_data'):
                del request.session[f'{new_agreement.id}-agreement_pricing_list_data']

            # Needed for fees and taxes
            locations_list = list(old_agreement.all_pricing_location_pks)
            new_locations_list = list(new_agreement.all_pricing_location_pks)

            # Associate Supplier-Defined Taxes and Associated Fees with the new PLD, if their form was interacted with
            # if not, then duplicate here
            # Always adjust the date if 'no_change' (date.today()) was indicated to the earliest fuel pricing entry
            if request.session.get(f'agreement-{new_agreement.id}-supplier-defined-taxes-saved'):

                # Delete taxes for locations that no longer apply (fuel pricing was removed), as to not keep
                # carrying them over (superseded by error)
                tax_entries = TaxRuleException.objects.filter(
                    Q(exception_organisation=old_agreement.supplier),
                    Q(source_agreement=old_agreement),
                    Q(exception_airport__in=locations_list),
                    Q(deleted_at__isnull=True), Q(valid_ufn=True))

                tax_deleted = False
                for entry in tax_entries:
                    if entry.exception_airport.id not in new_locations_list:
                        entry.delete()
                        tax_deleted = True

                if tax_deleted:
                    messages.warning(request, 'Supplier-Defined Tax deleted because of missing fuel pricing location')

                # Old Entries
                old_entries = TaxRuleException.objects.filter(
                    Q(exception_organisation=new_agreement.supplier),
                    Q(exception_airport__in=new_locations_list),
                    Q(deleted_at__isnull=True), Q(valid_ufn=False), Q(source_agreement=old_agreement))

                for entry in old_entries:
                    if entry.valid_to == date.today() - timedelta(days=1):
                        entry.valid_to = new_agreement.start_date - timedelta(days=1)
                        entry.save()

                # Adjust New Entries
                all_entries = TaxRuleException.objects.filter(Q(exception_organisation=new_agreement.supplier),
                                                              Q(exception_airport__in=new_locations_list),
                                                              Q(deleted_at__isnull=True), Q(valid_ufn=True))

                # New Entries
                for entry in all_entries:
                    entry.source_agreement = new_agreement
                    # This only works if supersede happens on the same day (basically we get 'no_change' entries)
                    if entry.valid_from == date.today():
                        entry.valid_from = new_agreement.start_date
                    entry.save()

            else:
                # Store existing
                main_entries = TaxRuleException.objects.filter(source_agreement=old_agreement, deleted_at__isnull=True,
                                                               parent_entry=None)

                # Init for taxable exception shift checking
                exceptions_main_tax = {}
                tax_entries = TaxRuleException.objects.filter(deleted_at__isnull=True, valid_ufn=True,
                                                              source_agreement=old_agreement)
                for entry in tax_entries:
                    exceptions_main_tax[entry] = None

                for entry in main_entries:
                    entry.updated_by = request.user.person
                    entry.valid_ufn = False
                    entry.valid_to = new_agreement.start_date - timedelta(days=1)

                    for child_entry in entry.child_entries.all():
                        child_entry.updated_by = request.user.person
                        child_entry.valid_ufn = False
                        child_entry.valid_to = new_agreement.start_date - timedelta(days=1)
                        child_entry.save()
                    entry.save()

                # Create New
                for entry in main_entries:
                    child_entries = entry.child_entries.all()
                    entry.updated_by = request.user.person
                    entry.valid_ufn = True
                    entry.valid_to = None
                    entry.valid_from = new_agreement.start_date
                    entry.source_agreement = new_agreement
                    current_entry = copy.deepcopy(entry)
                    entry.id = None
                    entry.save()
                    parent_entry = copy.deepcopy(entry)
                    exceptions_main_tax.update({current_entry: entry})

                    for child_entry in child_entries:
                        child_entry.updated_by = request.user.person
                        child_entry.valid_ufn = True
                        child_entry.valid_to = None
                        child_entry.valid_from = new_agreement.start_date
                        child_entry.parent_entry = parent_entry
                        child_entry.source_agreement = new_agreement
                        current_child_entry = copy.deepcopy(child_entry)
                        child_entry.id = None
                        child_entry.save()
                        exceptions_main_tax.update({current_child_entry: child_entry})

                for new_entry in main_entries:
                    if new_entry.taxable_exception is not None and exceptions_main_tax.get(
                        new_entry.taxable_exception) is not None:
                        new_entry.taxable_exception = exceptions_main_tax[new_entry.taxable_exception]
                        new_entry.save()

            if request.session.get(f'agreement-{new_agreement.id}-associated-fee-saved'):

                # Delete fees for locations that no longer apply (fuel pricing was removed), as to not keep
                # carrying them over (superseded by error)
                fee_entries = SupplierFuelFeeRate.objects.filter(Q(price_active=True), Q(deleted_at__isnull=True),
                                                                 Q(supplier_fuel_fee__supplier=new_agreement.supplier),
                                                                 Q(source_agreement=old_agreement),
                                                                 Q(supplier_fuel_fee__location__in=locations_list))

                fee_deleted = False
                for entry in fee_entries:
                    if entry.supplier_fuel_fee.location.id not in new_locations_list:
                        entry.supplier_fuel_fee.delete()
                        entry.delete()
                        tax_deleted = True

                if fee_deleted:
                    messages.warning(request, 'Associated Fee deleted because of missing fuel pricing location')

                # Adjust New Entries (only in relation to the new PLD's locations)
                all_entries = SupplierFuelFeeRate.objects.filter(Q(price_active=True), Q(deleted_at__isnull=True),
                                                                 Q(supplier_fuel_fee__supplier=new_agreement.supplier),
                                                                 Q(source_agreement=old_agreement),
                                                                 Q(supplier_fuel_fee__location__in=new_locations_list))

                # New Entries
                for entry in all_entries:
                    entry.supplier_fuel_fee.source_agreement = new_agreement
                    entry.supplier_fuel_fee.save()
                    # This only works if supersede happens on the same day (basically we get 'no_change' entries)
                    if entry.valid_from_date == date.today() and entry.valid_from_date != new_agreement.start_date:
                        entry.valid_from_date = new_agreement.start_date
                    entry.save()

                # Old Entries (only if the location is in the new PLD as well)
                old_entries = SupplierFuelFeeRate.objects.filter(Q(price_active=False), Q(deleted_at__isnull=True),
                                                                 Q(supplier_fuel_fee__supplier=new_agreement.supplier),
                                                                 Q(source_agreement=old_agreement),
                                                                 Q(supplier_fuel_fee__location__in=new_locations_list))

                for entry in old_entries:
                    if entry.valid_to_date == date.today() - timedelta(days=1):
                        entry.valid_to_date = new_agreement.start_date
                        entry.save()

            else:
                # Store existing
                all_entries = SupplierFuelFeeRate.objects.filter(source_agreement=old_agreement,
                                                                 deleted_at__isnull=True)

                for entry in all_entries:
                    entry.updated_by = request.user.person
                    entry.price_active = False
                    entry.valid_to_date = new_agreement.start_date - timedelta(days=1)
                    entry.save()

                all_fee_entries = SupplierFuelFee.objects.filter(rates__in=all_entries).distinct('id')

                # Create New
                for fee_entry in all_fee_entries:
                    rates = copy.deepcopy(fee_entry.rates.all())
                    fee_entry.id = None
                    fee_entry.save()

                    for entry in rates:
                        entry.source_agreement = new_agreement
                        entry.updated_by = request.user.person
                        entry.price_active = True
                        entry.valid_to_date = None
                        entry.valid_from_date = new_agreement.start_date
                        entry.supplier_fuel_fee = fee_entry

                        # Get existing validity periods
                        validity_periods = list(entry.validity_periods.all())

                        entry.id = None
                        entry.save()

                        # Copy validity periods to new instance
                        for period in validity_periods:
                            period.fuel_fee_rate = entry
                            period.pk = None
                            period.save()

            messages.success(request, 'Document superseded successfully')
            return HttpResponseRedirect(reverse_lazy('admin:fuel_agreement', kwargs={'pk': new_agreement.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'associated_fee_saved': request.session.get(f'agreement-{new_agreement.id}-associated-fee-saved', None),
                'supplier_defined_tax_saved': request.session.get(
                    f'agreement-{new_agreement.id}-supplier-defined-taxes-saved', None),
                'document': new_agreement,
                'related_entries_formula': related_entries_formula,
                'related_entries_discount': related_entries_discount,
                'pricing_formset_formula': pricing_formset_formula,
                'pricing_formset_discount': pricing_formset_discount,
                'metacontext': self.metacontext,
            })
