import copy
import json
from datetime import datetime, timedelta, date

from django.db import transaction
from django.db.models import Case, CharField, Exists, F, OuterRef, Q, Value, When
from django.db.models.functions import Concat
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, DetailView
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalFormView, BSModalUpdateView, BSModalDeleteView
from bootstrap_modal_forms.mixins import is_ajax

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_badge
from organisation.models.organisation import Organisation
from pricing.forms import FuelPricingMarketPldForm, FuelPricingMarketPldBillableOrganisationsForm, \
    FuelPricingMarketPldBillableOrganisationsFormset, FuelPricingMarketPricingFormset, \
    NewFuelPricingMarketPricingFormset, PLDDocumentsForm, PricingDatesSupersedeForm
from pricing.models import FuelPricingMarket, FuelPricingMarketPld, FuelPricingMarketPldDocument, \
    FuelPricingMarketPldLocation, SupplierFuelFee, SupplierFuelFeeRate, TaxRuleException
from pricing.utils.fuel_pricing_market import get_datatable_airport_location, get_datatable_pld_status_with_formatting,\
    get_datatable_pld_button_logic
from pricing.utils.session import serialize_request_data
from user.mixins import AdminPermissionsMixin


## FUEL PRICING - supplier_fuel_pricing_market ##
## ASSOCIATED FEES - supplier_fuel_fees ##
## SUPPLIER-DEFINED TAXES - tax_rule_exceptions ##
## If needed, the last one should be checked for overall logic

## Fuel Pricing has a set valid from / to dates (we can think of it as the PLD's validity)
## However, fees and taxes are always valid ufn, and are only modified on supersede (or deletion)

# List view for PLDs
class FuelPricingMarketPldListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelPricingMarketPld
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        qs = FuelPricingMarketPld.objects.with_pld_status().filter(is_current=True)

        qs = qs.annotate(
            name_str=Case(
                When(supplier__details__trading_name__isnull=False, then=Concat(
                    'supplier__details__trading_name',
                    Value(' ('),
                    'supplier__details__registered_name',
                    Value(')'),
                    output_field=CharField())),
                default=F('supplier__details__registered_name')
            )
        )

        return qs

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
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)


        if 'pld_status' in column_names:
                # Use comma instead of the regular self.search_values_separator
                search_value = [t.strip() for t in search_value.split(',')]
                if 'All' in search_value:
                    search_value = ['All', 'Pricing Expired', 'Partial Pricing Expiry', 'OK', 'No Pricing']

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)

        elif 'locations' in column_names:
            return qs.filter(Q(locations__airport_details__icao_code__istartswith=search_value) |
                             Q(locations__airport_details__iata_code__istartswith=search_value)
                             ).distinct()
        else:
            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                global_filtering)
            if column_filter:
                search_filters |= column_filter

            return qs.filter(search_filters)

    default_status_filter = 'All'

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px' },
        {'name': 'name_str', 'title': 'Supplier', 'className': 'organisation_reg_name'},
        {'name': 'pld_name', 'title': 'PLD Name', 'max_length': 80},
        {'name': 'locations', 'title': 'Location(s)', 'className': 'location', 'placeholder': True, 'orderable': False},
        {'name': 'pld_status', 'title': 'Status', 'placeholder': True, 'searchable': True, 'orderable': False,
         'className': 'link multiple-select-filter-col mission-status pld_status',
         'initialSearchValue': default_status_filter,
         'choices': (
             ('All', 'All'),
             ('Pricing Expired', 'Pricing Expired'),
             ('Partial Pricing Expiry', 'Partial Pricing Expiry'),
             ('OK', 'OK'),
             ('No Pricing', 'No Pricing'),
         ),
         },
        {'name': 'publication_status', 'title': 'Published', 'placeholder': True,
         'searchable': False, 'orderable': False, 'className': 'pld_publication_status', 'width': '50px'},
        {'name': 'actions', 'title': 'Actions', 'placeholder': True,
         'searchable': False, 'className': 'pld_actions','orderable': False},
    ]

    def customize_row(self, row, obj):
        row['supplier'] = Organisation.objects.get(id = obj.supplier_id).trading_or_registered_name
        row['locations'] = get_datatable_airport_location(obj.id)
        row['pld_status'] = get_datatable_pld_status_with_formatting(obj.pld_status)
        row['actions'] = get_datatable_pld_button_logic(self, row, obj)

        fuel_pricing = FuelPricingMarket.objects.filter(supplier_pld_location__in = obj.pld_at_location.all(),
                                                        price_active = True,
                                                        deleted_at__isnull = True)
        has_published = False
        has_unpublished = False
        partially_published = False

        if fuel_pricing.filter(is_published = True):
            has_published = True

        if fuel_pricing.filter(is_published = False):
            has_unpublished = True

        if has_published and has_unpublished:
            partially_published = True

        if partially_published:
            row['publication_status'] = get_datatable_badge(
                                                    badge_text='Partially Published',
                                                    badge_class='bg-warning datatable-badge-normal publication_status')
        elif has_published:
            row['publication_status'] = get_datatable_badge(
                                                    badge_text='Published',
                                                    badge_class='bg-success datatable-badge-normal publication_status')

        else:
            row['publication_status'] = get_datatable_badge(
                                                    badge_text='Unpublished',
                                                    badge_class="bg-danger datatable-badge-normal publication_status")


        return


class FuelPricingMarketPldListView(AdminPermissionsMixin, TemplateView):
    template_name = 'fuel_pricing_market_updates_document_list.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Fuel Pricing Update',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:fuel_pricing_market_documents_create'),
             'button_modal': True,
             'button_perm': self.request.user.has_perm('pricing.p_create')},
        ]

        metacontext = {
            'title': 'Fuel Market Pricing Updates',
            'page_id': 'market_pricing_list',
            'page_css_class': ' datatable-clickable',
            'datatable_uri': 'admin:fuel_pricing_market_documents_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
            'multiple_select_filters': True,
        }

        context['metacontext'] = metacontext
        return context


# Supersede Section Starts
# Fuel Pricing
class FuelPricingMarketPldSupersedeFuelPricingView(AdminPermissionsMixin, TemplateView):
    template_name = 'fuel_pricing_market_updates_document_supersede_fuel_pricing.html'
    permission_required = ['pricing.p_create']

    def get(self, request, *args, **kwargs):
        document = FuelPricingMarketPld.objects.get(pk=self.kwargs.get('pk', None))

        if not document.is_current:
            messages.error(request, 'The document has already been superseded')
            return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_documents'))

        # If coming from the CSV Importer page, and overrides exist,
        # apply them on original pricing, and ignore any previously saved data
        redirect_from_import = reverse('admin:fuel_market_pricing_csv_importer') in request.META.get('HTTP_REFERER', '')
        importer_updates = request.session.get(f'{document.id}-pricing_list_data_overrides', None) \
            if redirect_from_import else None

        if importer_updates:
            messages.info(request, 'CSV Importer data was used to update pricing and dates.')

            # Disable fees and/or taxes if no changes indicated on importer page
            # Clear any previously saved data first, to ensure we get 'no change' on the defaults.
            request.session.pop(f'pld-{document.id}-associated_fees_data', None)
            request.session.pop(f'pld-{document.id}-supplier_tax_data', None)
            request.session[f'pld-{document.id}-associated-fee-saved'] = not importer_updates['changes_to_fees']
            request.session[f'pld-{document.id}-supplier-defined-taxes-saved'] = not importer_updates['changes_to_taxes']

        related_entries = FuelPricingMarket.objects.filter(Q(supplier_pld_location__in = document.pld_at_location.all()),
                                                           Q(price_active = True),
                                                          ~Q(parent_entry = None)).order_by('band_start')


        pricing_formset = FuelPricingMarketPricingFormset(
            form_kwargs={'pld_instance': document, 'context': 'Supersede'},
            importer_updates=importer_updates, pld_instance=document, context='Supersede',
            prefix='existing-pricing'
        )

        # Check the checkbox if all dates match
        first_from_date = first_to_date = ''
        all_dates_match = False
        if len(pricing_formset) > 1:
            first_from_date = pricing_formset[0]['valid_from_date'].initial
            first_to_date = pricing_formset[0]['valid_to_date'].initial
            all_dates_match = True
            for field in pricing_formset:
                if field['valid_from_date'].initial != first_from_date \
                    or field['valid_to_date'].initial != first_to_date:
                    all_dates_match = False
                    first_from_date = first_to_date = ''

        update_date_form = PricingDatesSupersedeForm(context='fuel-pricing',
                                                     initial={'apply_to_all': all_dates_match,
                                                              'valid_from': first_from_date,
                                                              'valid_to': first_to_date},
                                                     prefix='update-date')

        # For Debugging purposes
        # del request.session[f'{document.id}-pricing_list_data']

        # for key in dict(request.session):
        #    if str(document.id) in key:
        #         del request.session[key]

        if not importer_updates and f'{document.id}-pricing_list_data' in request.session:
            session_data = request.session[f'{document.id}-pricing_list_data']

            form_numbers = session_data.get('existing-pricing-TOTAL_FORMS')

            extra_fields = {i: 0 for i in range(int(form_numbers))}
            for form_number in extra_fields:
                for key in session_data:
                    if f'-{form_number}-band_start-additional' in key:
                        extra_fields[form_number] += 1

            pricing_formset = FuelPricingMarketPricingFormset(
                                                        data = session_data,
                                                        form_kwargs={'pld_instance': document,'context': 'Supersede'},
                                                        pld_instance=document, context='Supersede',
                                                        extra_fields=extra_fields, prefix='existing-pricing')

            if len(pricing_formset) > 1:
                first_from_date = pricing_formset[0]['valid_from_date'].initial
                first_to_date = pricing_formset[0]['valid_to_date'].initial
                all_dates_match = True
                for form in pricing_formset:
                    if form['valid_from_date'].initial != first_from_date \
                        or form['valid_to_date'].initial != first_to_date:
                        all_dates_match = False
                        first_from_date = first_to_date = ''

                update_date_form = PricingDatesSupersedeForm(session_data,
                                                             context='fuel-pricing',
                                                             initial={'apply_to_all': all_dates_match,
                                                                      'valid_from': first_from_date,
                                                                      'valid_to': first_to_date},
                                                             prefix='update-date')

        return self.render_to_response({
            'associated_fee_saved': request.session.get(f'pld-{document.id}-associated-fee-saved', None),
            'supplier_defined_tax_saved': request.session.get(f'pld-{document.id}-supplier-defined-taxes-saved', None),
            'all_dates_match': all_dates_match,
            'document': document,
            'update_date_form': update_date_form,
            'related_entries': related_entries,
            'document_pricing_formset': pricing_formset
        })

    def post(self, request, *args, **kwargs):
        document = FuelPricingMarketPld.objects.get(pk=self.kwargs.get('pk', None))
        related_entries = FuelPricingMarket.objects.filter(
                    Q(supplier_pld_location__in = document.pld_at_location.all()),
                    Q(price_active = True),
                    ~Q(parent_entry = None))

        dates_entered = False
        if request.POST.get('update-date-valid_from') and request.POST.get('update-date-valid_to'):
            dates_entered = True

        form_numbers = request.POST.get('existing-pricing-TOTAL_FORMS')

        extra_fields = {i: 0 for i in range(int(form_numbers))}
        for form_number in extra_fields:
            for key in request.POST:
                if f'-{form_number}-band_start-additional' in key:
                    extra_fields[form_number] += 1

        pricing_formset = FuelPricingMarketPricingFormset(request.POST,
                                                          form_kwargs={'pld_instance': document, 'context': 'Supersede'},
                                                          pld_instance=document, context='Supersede',
                                                          dates_entered=dates_entered, extra_fields=extra_fields,
                                                          prefix='existing-pricing')

        update_date_form = PricingDatesSupersedeForm(request.POST,
                                                     context='fuel-pricing',
                                                     prefix='update-date')

        if 'taxes' in request.POST['button-pressed']:
            request.session[f'{document.id}-pricing_list_data'] = serialize_request_data(request.POST)

            messages.info(request, 'Fuel Pricing form fields were saved')
            return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_documents_supersede_supplier_taxes',
                                                    kwargs={'pk': document.id}))

        elif 'associated-fees' in request.POST['button-pressed']:
            request.session[f'{document.id}-pricing_list_data'] = serialize_request_data(request.POST)

            messages.info(request, 'Fuel Pricing form fields were saved')
            return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_documents_supersede_associated_fees',
                                                    kwargs={'pk': document.id}))

        elif 'supersede' in request.POST['button-pressed']:
            # Check if fees / taxes change is required (info saved in management form)
            # and if yes, prevent supersede and return form with a warning.
            missing_elements = []

            fees_required = pricing_formset.management_form['require_change_in_fees'].value() == 'True'
            fees_saved = request.session.get(f'pld-{document.id}-associated-fee-saved', None)

            if fees_required and not fees_saved:
                missing_elements.append('Associated Fees')

            taxes_required = pricing_formset.management_form['require_change_in_taxes'].value() == 'True'
            taxes_saved = request.session.get(f'pld-{document.id}-supplier-defined-taxes-saved', None)

            if taxes_required and not taxes_saved:
                missing_elements.append('Supplier-Defined Taxes')

            if missing_elements:
                messages.error(request, f"Please update the {' and '.join(missing_elements)} before"
                                        f" superseding.")

                return self.render_to_response({
                    'associated_fee_saved': request.session.get(f'pld-{document.id}-associated-fee-saved', None),
                    'supplier_defined_tax_saved': request.session.get(f'pld-{document.id}-supplier-defined-taxes-saved',
                                                                      None),
                    'related_entries': related_entries,
                    'document_pricing_formset': pricing_formset,
                    'document': document,
                    'update_date_form': update_date_form,
                })

        if all([
            pricing_formset.is_valid(),
            update_date_form.is_valid(),
        ]):

            # Create new document
            new_document = FuelPricingMarketPld.objects.create(pld_name = document.pld_name, is_current = True,
                                                                   supplier = document.supplier,
                                                                   updated_by = request.user.person)

            # Supersede the previous document
            document.is_current = False
            document.updated_by = request.user.person
            document.save()

            # Note: have to save(commit=False) to access deleted_objects
            formset = pricing_formset.save(commit=False)

            # Save existing pricing as new
            for count, form in enumerate(pricing_formset):
                instance = form.save(commit=False)

                if instance in pricing_formset.deleted_objects:
                    # Preserve deleted entry and its children

                    # We actually need to reuse the DB values here, otherwise we save what was entered in the form.
                    instance.refresh_from_db()
                    instance.price_active = False
                    instance.is_latest = False
                    instance.save()

                    related_entries = FuelPricingMarket.objects.filter(parent_entry_id = instance.id)\
                                                                   .update(price_active = False, is_latest = False)
                else:
                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    # Preserve what's superseded, and also fix date collision (if any)
                    # The new entry's valid_from_date should never be earlier than the old one's =>
                    # I assume fuel suppliers are not going to change pricing retroactively...
                    entry = FuelPricingMarket.objects.get(id = instance.id)
                    related_entries = FuelPricingMarket.objects.filter(parent_entry_id = instance.id)

                    entry.price_active = False
                    entry.is_latest = False

                    for obj in related_entries:
                        obj.price_active = False
                        obj.is_latest = False

                    if update_date_form.changed_data:
                        instance.valid_from_date = update_date_form.cleaned_data['valid_from']
                        instance.valid_to_date = update_date_form.cleaned_data['valid_to']

                    if entry.valid_to_date > instance.valid_from_date:

                        entry.valid_to_date = instance.valid_from_date - timedelta(days=1)

                        for obj in related_entries:
                            obj.valid_to_date = instance.valid_from_date - timedelta(days=1)

                    elif entry.valid_from_date < instance.valid_from_date:
                        # ...but if they do then let's just set as inactive for now
                        pass

                    entry.save()
                    FuelPricingMarket.objects.bulk_update(related_entries, ["price_active", "is_latest", "valid_to_date"])

                    # Create new entries
                    instance.supplier_pld_location = \
                        FuelPricingMarketPldLocation.objects.get_or_create(
                            pld_id=new_document.id,
                            location=instance.supplier_pld_location.location,
                            billable_organisation=instance.supplier_pld_location.billable_organisation)[0]

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    instance.price_active = True
                    instance.is_latest = True
                    instance.is_published = False
                    instance.is_reviewed = False
                    instance.review_id = None

                    if instance.supplier_exchange_rate:
                        instance.convert_pricing_amount()

                    instance.id = None
                    instance.updated_by = request.user.person
                    instance.parent_entry = None
                    instance.save()

                    # Update included taxes and DMs (M2M, must be done after new instance is saved)
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
                            if f'-{count}-band_start' in key and value != "":
                                instance.band_start = value
                                continue
                            if f'-{count}-band_end' in key and value != "":
                                instance.band_end = value
                                continue
                            if f'-{count}-band_pricing_native_amount' in key and 'old' not in key:
                                instance.pricing_native_amount = value

                                if instance.supplier_exchange_rate:
                                    instance.convert_pricing_amount()

                                instance.parent_entry = parent_entry
                                instance.save()

                                instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                                instance.id = None

            request.session.pop(f'{document.id}-pricing_list_data', None)
            request.session.pop(f'{document.id}-pricing_list_data_overrides', None)

            earliest_fuel_pricing = FuelPricingMarket.objects.filter(
                price_active=True, parent_entry=None,
                supplier_pld_location__in=new_document.pld_at_location.all()
            ).order_by('valid_from_date').first()

            # Needed for fees and taxes
            locations_list = list(document.pld_at_location.all().values_list('location', flat=True))
            new_locations_list = list(new_document.pld_at_location.all().values_list('location', flat=True))

            # Associate Supplier-Defined Taxes and Associated Fees with the new PLD, if their form was interacted with
            # if not, then duplicate here
            # Always adjust the date if 'no_change' (date.today()) was indicated to the earliest fuel pricing entry
            if request.session.get(f'pld-{document.id}-supplier-defined-taxes-saved'):

                # Delete taxes for locations that no longer apply (fuel pricing was removed), as to not keep
                # carrying them over (superseded by error)
                tax_entries = TaxRuleException.objects.filter(\
                                    Q(exception_organisation = document.supplier),
                                    Q(related_pld = document),
                                    Q(exception_airport__in = locations_list),
                                    Q(deleted_at__isnull = True), Q(valid_ufn = True))

                tax_deleted = False
                for entry in tax_entries:
                    if entry.exception_airport.id not in new_locations_list:
                        entry.delete()
                        tax_deleted = True

                if tax_deleted:
                        messages.warning(request, 'Supplier-Defined Tax deleted because of missing fuel pricing location')


                # Old Entries
                old_entries = TaxRuleException.objects.filter(\
                                            Q(exception_organisation = document.supplier),
                                            Q(exception_airport__in = new_locations_list),
                                            Q(deleted_at__isnull = True), Q(valid_ufn = False), Q(related_pld = document))

                for entry in old_entries:
                    if entry.valid_to == date.today() - timedelta(days=1):
                        entry.valid_to = earliest_fuel_pricing.valid_from_date - timedelta(days=1)
                        entry.save()

                # Adjust New Entries
                all_entries = TaxRuleException.objects.filter(Q(exception_organisation = document.supplier),
                                                              Q(exception_airport__in = new_locations_list),
                                                              Q(deleted_at__isnull = True), Q(valid_ufn = True))

                # New Entries
                for entry in all_entries:
                    entry.related_pld = new_document
                    # This only works if supersede happens on the same day (basically we get 'no_change' entries)
                    if entry.valid_from == date.today() and entry.valid_from != earliest_fuel_pricing.valid_from_date:
                        entry.valid_from = earliest_fuel_pricing.valid_from_date
                    entry.save()

            else:
                # Store existing
                main_entries = TaxRuleException.objects.filter(related_pld = document, deleted_at__isnull = True,
                                                                   parent_entry = None)

                # Init for taxable exception shift checking
                exceptions_main_tax = {}
                tax_entries = TaxRuleException.objects.filter(deleted_at__isnull=True, valid_ufn=True, related_pld=document)
                for entry in tax_entries:
                    exceptions_main_tax[entry] = None

                for entry in main_entries:
                    entry.updated_by = request.user.person
                    entry.valid_ufn = False
                    entry.valid_to = earliest_fuel_pricing.valid_from_date - timedelta(days=1)

                    for child_entry in entry.child_entries.all():
                        child_entry.updated_by = request.user.person
                        child_entry.valid_ufn = False
                        child_entry.valid_to = earliest_fuel_pricing.valid_from_date - timedelta(days=1)
                        child_entry.save()
                    entry.save()

                # Create New
                for entry in main_entries:
                    child_entries = entry.child_entries.all()
                    entry.updated_by = request.user.person
                    entry.valid_ufn = True
                    entry.valid_to = None
                    entry.valid_from = earliest_fuel_pricing.valid_from_date
                    entry.related_pld = new_document
                    current_entry = copy.deepcopy(entry)
                    entry.id = None
                    entry.save()
                    parent_entry = copy.deepcopy(entry)
                    exceptions_main_tax.update({current_entry: entry})

                    for child_entry in child_entries:
                        child_entry.updated_by = request.user.person
                        child_entry.valid_ufn = True
                        child_entry.valid_to = None
                        child_entry.valid_from = earliest_fuel_pricing.valid_from_date
                        child_entry.parent_entry = parent_entry
                        child_entry.related_pld = new_document
                        current_child_entry = copy.deepcopy(child_entry)
                        child_entry.id = None
                        child_entry.save()
                        exceptions_main_tax.update({current_child_entry: child_entry})

                for new_entry in main_entries:
                    if new_entry.taxable_exception is not None and exceptions_main_tax.get(new_entry.taxable_exception) is not None:
                        new_entry.taxable_exception = exceptions_main_tax[new_entry.taxable_exception]
                        new_entry.save()

            if request.session.get(f'pld-{document.id}-associated-fee-saved'):

                # Delete fees for locations that no longer apply (fuel pricing was removed), as to not keep
                # carrying them over (superseded by error)
                fee_entries = SupplierFuelFeeRate.objects.filter(Q(price_active = True), Q(deleted_at__isnull = True),
                                                                 Q(supplier_fuel_fee__supplier = document.supplier),
                                                                 Q(supplier_fuel_fee__related_pld = document),
                                                                 Q(supplier_fuel_fee__location__in = locations_list))

                fee_deleted = False
                for entry in fee_entries:
                    if entry.supplier_fuel_fee.location.id not in new_locations_list:
                        entry.supplier_fuel_fee.delete()
                        entry.delete()
                        tax_deleted = True

                if fee_deleted:
                    messages.warning(request, 'Associated Fee deleted because of missing fuel pricing location')

                # Adjust New Entries (only in relation to the new PLD's locations)
                all_entries = SupplierFuelFeeRate.objects.filter(Q(price_active = True), Q(deleted_at__isnull = True),
                                                                 Q(supplier_fuel_fee__supplier = document.supplier),
                                                                 Q(supplier_fuel_fee__related_pld = document),
                                                                 Q(supplier_fuel_fee__location__in = new_locations_list))

                # New Entries
                for entry in all_entries:
                    entry.supplier_fuel_fee.related_pld = new_document
                    entry.supplier_fuel_fee.save()
                    # This only works if supersede happens on the same day (basically we get 'no_change' entries)
                    if entry.valid_from_date == date.today() and entry.valid_from_date != earliest_fuel_pricing.valid_from_date:
                        entry.valid_from_date = earliest_fuel_pricing.valid_from_date
                    entry.save()

                # Old Entries (only if the location is in the new PLD as well)
                old_entries = SupplierFuelFeeRate.objects.filter(Q(price_active = False), Q(deleted_at__isnull = True),
                                                                 Q(supplier_fuel_fee__supplier = document.supplier),
                                                                 Q(supplier_fuel_fee__related_pld = document),
                                                                 Q(supplier_fuel_fee__location__in = new_locations_list))

                for entry in old_entries:
                    if entry.valid_to_date == date.today() - timedelta(days=1):
                        entry.valid_to_date = earliest_fuel_pricing.valid_from_date
                        entry.save()

            else:
                # Store existing
                all_entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee__related_pld = document,
                                                                     deleted_at__isnull = True)

                for entry in all_entries:
                    entry.updated_by = request.user.person
                    entry.price_active = False
                    entry.valid_to_date = earliest_fuel_pricing.valid_from_date - timedelta(days=1)
                    entry.save()

                all_fee_entries = SupplierFuelFee.objects.filter(rates__in = all_entries).distinct('id')

                # Create New
                for fee_entry in all_fee_entries:
                    fee_entry.related_pld = new_document
                    rates = copy.deepcopy(fee_entry.rates.all())
                    fee_entry.id = None
                    fee_entry.save()

                    for entry in rates:
                        entry.updated_by = request.user.person
                        entry.price_active = True
                        entry.valid_to_date = None
                        entry.valid_from_date = earliest_fuel_pricing.valid_from_date
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
            return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                        kwargs={'pk': new_document.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'associated_fee_saved': request.session.get(f'pld-{document.id}-associated-fee-saved', None),
                'supplier_defined_tax_saved': request.session.get(f'pld-{document.id}-supplier-defined-taxes-saved', None),
                'related_entries': related_entries,
                'document_pricing_formset': pricing_formset,
                'document': document,
                'update_date_form': update_date_form,
                })


# Supersede Section Ends


# Publish/Unpublish pricing
class FuelPricingMarketAlterPublicationStatus(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    model = FuelPricingMarketPld
    success_message = 'Pricing document publication status changed successfully'
    permission_required = ['pricing.p_publish']

    def get_success_url(self):
         return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        self.document = get_object_or_404(FuelPricingMarketPld, pk=self.kwargs['pk'])
        self.action = self.kwargs['action']

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Change pricing publication status',
            'text': f'You are about to {self.action} all active pricing attached to "{self.document.pld_name}".',
            'icon': 'fa-plus',
            'action_button_text': 'Confirm',
            'action_button_class': 'btn-danger'
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, commit=True):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                with transaction.atomic():

                    market_entries_to_update = FuelPricingMarket.objects.filter(
                                    supplier_pld_location__pld = self.document, price_active = True)

                    for entry in market_entries_to_update:
                        if(self.action == 'publish'):
                            entry.is_published = True
                        else:
                            entry.is_published = False
                    FuelPricingMarket.objects.bulk_update(market_entries_to_update, ['is_published'])

        return super().form_valid(form)


# Create PLD
class FuelPricingMarketPldCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = FuelPricingMarketPld
    form_class = FuelPricingMarketPldForm
    success_message = 'Pricing document created successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return reverse_lazy('admin:fuel_pricing_market_documents_pricing_create_page', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create New Fuel Pricing Document',
            'icon': 'fa-plus',
            'action_button_text': 'Save and Continue',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save(commit=False)

        return super().form_valid(form)

    # Update: The special usage of modal_button_novalidation in datatables.js could now be removed after updating
    # to django_bootstrap_modal_forms 3, however this update also broke the page (the new instance would save,
    # but get_success_url would again fail to obtain the self.object, even with modal_button_novalidation).
    # Apparently, by default only the form_valid in FormValidationMixin is called, which never sets self.object,
    # and the one in ModelFormMixin is skipped over.
    # This seems to be fixed by setting self.object in the overridden form_valid above. Now the model saves,
    # redirection on success works, and the success message is only displayed once, and even the name validation
    # could be restored. - LP


# PLD Details
class FuelPricingMarketPldDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'fuel_pricing_market_updates_document_details.html'
    model = FuelPricingMarketPld
    context_object_name = 'document'
    permission_required = ['pricing.p_view']

    def get_object(self):
        return FuelPricingMarketPld.objects.with_pld_status().get(id = self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        document = self.object

        fuel_pricing = FuelPricingMarket.objects.filter(price_active = True,
                                                        supplier_pld_location__in = document.pld_at_location.all())\
                                                .exists()

        locations = document.pld_at_location.all().values('location')
        countries = document.pld_at_location.all().values('location__details__country')

        associated_fees = SupplierFuelFeeRate.objects.filter(Q(price_active = True),
                                                             Q(supplier_fuel_fee__supplier = document.supplier),
                                                             Q(supplier_fuel_fee__location__in = locations),
                                                             Q(supplier_fuel_fee__related_pld = document))\
                                                     .exists()


        supplier_taxes = TaxRuleException.objects.filter(Q(parent_entry = None),
                                                         Q(exception_organisation = document.supplier),
                                                         Q(deleted_at__isnull = True),
                                                         Q(valid_ufn = True),
                                                         Q(related_pld = document),
                                                         Q(Q(exception_airport__in = locations) |
                                                         Q(exception_country__in = countries))).exists()

        # When loading the page, the PLD is no longer considered new
        document = kwargs.get('object')
        if self.request.session.get(f'pld-{document.id}'):
            del self.request.session[f'pld-{document.id}']

        metacontext = {
            'fuel_pricing': fuel_pricing,
            'associated_fees': associated_fees,
            'supplier_defined_taxes': supplier_taxes
        }

        context['metacontext'] = metacontext
        return context


# PLD Edit
class FuelPricingMarketPldEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = FuelPricingMarketPld
    form_class = FuelPricingMarketPldForm
    success_message = 'Pricing document edited successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Fuel Pricing Document',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context


# Documents
class FuelPricingMarketPldDocumentListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelPricingMarketPldDocument
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        qs = FuelPricingMarketPldDocument.objects.filter(
            pld_id=self.kwargs['pk'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Name',  'visible': True, 'searchable': False},
        {'name': 'description', 'title': 'Description',  'visible': True, 'searchable': False, },
        {'name': 'actions', 'title': '', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'pld_page_actions_column'},
    ]

    def customize_row(self, row, obj):
        row['name'] = f'<span data-url="{obj.file.url}">{obj.name}</span>'

        download_btn = get_datatable_actions_button(button_text='',
                                                  button_url=obj.file.url,
                                                  button_class='fa-download text-primary',
                                                  button_active=self.request.user.has_perm(
                                                      'pricing.p_view'),
                                                  button_modal=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:fuel_pricing_market_documents_document_delete',
                                                       kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'pricing.p_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = download_btn + delete_btn
        return


# Document Create
class FuelPricingMarketPldDocumentCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = FuelPricingMarketPldDocument
    form_class = PLDDocumentsForm
    success_message = 'Document created successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        document = get_object_or_404(FuelPricingMarketPld, pk=self.kwargs['pk'])
        kwargs.update({'document': document})

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Upload New Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


# Document Delete
class FuelPricingMarketPldDocumentDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = FuelPricingMarketPldDocument
    form_class = ConfirmationForm
    success_message = 'Document has been deleted'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Document',
            'text': f'Are you sure you want to delete this document?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context


# PLD Tables Section Start
# Fuel Pricing List
class FuelPricingMarketFuelPricingListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelPricingMarket
    search_values_separator = '+'
    initial_order = [['icao_iata', "asc"]]
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_market_updates_document_fuel_pricing_list_subtable.html', {
            'object': FuelPricingMarket.objects.get(id=pk),
            'table_name': 'fuel_pricing'
        })

    def get_initial_queryset(self, request=None):

        # Note: annotate is not exactly necessary here, but then we need to do some manual column search stuff
        qs = FuelPricingMarket.objects.with_details().filter(parent_entry = None,
                                                             supplier_pld_location__pld = self.kwargs['pk'],
                                                             price_active = True)\
                                                     .annotate(validity_range =\
                                                               Concat('valid_from_date', Value(' - '),
                                                                      'valid_to_date', output_field=CharField()))
        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'icao_iata', 'title': 'Location', },
        {'name': 'fuel', 'title': 'Fuel', 'lookup_field': '__name__icontains' },
        {'name': 'ipa', 'title': 'IPA', 'foreign_field': 'ipa__details__registered_name',
         'defaultContent': 'TBC / Confirmed on Order'},
        {'name': 'destination_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'private_or_commercial', 'title': 'Operated As'},
        {'name': 'validity_range', 'title': 'Validity','placeholder': True},
        {'name': 'specific_client', 'title': 'Specific Client', 'visible': True, 'className': 'text-wrap',
         'defaultContent': '--'},
        {'name': 'pricing_native_amount', 'title': 'Pricing', 'orderable': True},
        {'name': 'is_pap', 'title': 'PAP', 'orderable': True, 'searchable': False},
        {'name': 'is_published', 'title': 'Status', 'searchable': False},
        {'name': 'actions', 'title': '',
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'pricing_native_amount' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.filter(Q(parent_entry = None)).order_by('band_uom')
            else:
                qs = qs.filter(Q(parent_entry = None)).order_by('-band_uom')
            return qs

        elif 'private_or_commercial' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.filter().order_by('applies_to_private')
            else:
                qs = qs.filter().order_by('-applies_to_private')
            return qs

        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'icao_iata')
            return qs

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
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'pricing_native_amount' in column_names:
            if 'band applies'.startswith(search_value.lower()):
                return qs.filter(~Q(band_uom = None))

            else:
                return qs.filter(Q(band_uom = None),
                                Q(pricing_native_unit__description__icontains=search_value) |
                                Q(pricing_converted_unit__description__icontains=search_value)
                                ).distinct()

        elif 'private_or_commercial' in column_names:
            if 'private'.startswith(search_value.lower()):
                return qs.filter(applies_to_private = True)
            elif 'commercial'.startswith(search_value.lower()):
                return qs.filter(applies_to_commercial = True)
            elif 'commercial, private'.startswith(search_value.lower()):
                return qs.filter(applies_to_commercial = True, applies_to_private = True)
            else:
                return qs.filter(applies_to_private = False, applies_to_commercial = False)

        else:
            return qs.filter(search_filters)

    def customize_row(self, row, obj):

        related_entries = FuelPricingMarket.objects.filter(parent_entry = obj.pk, price_active = True)

        if related_entries.exists() or obj.band_uom:
            add_class = 'has_children'
            row['pricing_native_amount'] = f'Band Applies'
        else:
            add_class = ''
            row['pricing_native_amount'] = obj.get_pricing_datatable_str()

        # Note: modified children tables to be universal, we need 'has_children on one of the <td>s

        row['icao_iata'] = f'<span class="{add_class}"\>{obj.supplier_pld_location.location.airport_details.icao_iata}\
                            </span>'

        formatted_flight_type = (obj.flight_type.name).split('Only')[0].strip()
        if formatted_flight_type[-1] != 's': formatted_flight_type += 's'

        row['validity_range'] = f'{obj.valid_from_date} - {obj.valid_to_date}'
        row['flight_type'] = formatted_flight_type
        if obj.applies_to_private and obj.applies_to_commercial:
            row['private_or_commercial'] = 'Commercial, Private'
        else:
            row['private_or_commercial'] = 'Private' if obj.applies_to_private else 'Commercial'

        if obj.is_published:
            publication_status = 'Published'
        else:
            publication_status = 'Unpublished'

        if obj.valid_to_date >= date.today():
            row['is_published'] = f'OK / {publication_status}'
        else:
            row['is_published'] = f'Expired / {publication_status}'

        view_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:fuel_pricing_market_documents_pricing_details',
                                                            kwargs={'pk': obj.pk}),
                                                        button_class='fa-eye',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_view'),
                                                        button_modal=False,
                                                        modal_validation=True)

        edit_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:fuel_pricing_market_documents_pricing_edit',
                                                            kwargs={'pk': obj.pk,
                                                                    'pld': obj.supplier_pld_location.pld.id}),
                                                        button_class='fa-edit',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=False)

        archive_btn = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:fuel_pricing_market_documents_fuel_pricing_archive',
                                                            kwargs={'pk': obj.pk}),
                                                        button_class='fa-trash text-danger',
                                                        button_active=self.request.user.has_perm(
                                                            'pricing.p_update'),
                                                        button_modal=True,
                                                        modal_validation=False)

        row['actions'] = view_btn + edit_btn + archive_btn
        return


# Fuel Pricing Subtable
class FuelPricingMarketFuelPricingSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelPricingMarket
    search_values_separator = '+'
    initial_order = [['band_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = FuelPricingMarket.objects.filter(id=self.kwargs['pk'])
        related_entries = FuelPricingMarket.objects.filter(parent_entry = self.kwargs['pk'])

        qs = parent_entry.union(related_entries).order_by('band_start')

        # Not sure if it impacts performance too much, but I'm only disabling it for the subtable
        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_start', 'title': 'Bands', 'placeholder': True, 'width': '213px'},
        {'name': 'pricing_native_amount', 'title': 'Native Pricing', 'placeholder': True},
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_6', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_7', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_8', 'title': 'Bands', 'placeholder': True,},

    ]

    def customize_row(self, row, obj):

        # Not the best solution, but it gives a better overall look
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        row['band_start'] = f'{obj.band_uom}: {int(obj.band_start)} - {int(obj.band_end)}'
        row['pricing_native_amount'] = obj.get_pricing_datatable_str()


# Associated Fees
class FuelPricingMarketAssociatedFeesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFeeRate
    search_values_separator = '+'
    initial_order = [['supplier_fuel_fee', "asc"]]
    permission_required = ['pricing.p_view']


    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_market_updates_document_associated_fee_list_subtable.html', {
            'object': SupplierFuelFeeRate.objects.get(id=pk),
            'table_name': 'fuel_fee'
        })

    def get_initial_queryset(self, request=None):
        self.document = FuelPricingMarketPld.objects.get(id = self.kwargs['pk'])
        self.locations = FuelPricingMarketPldLocation.objects.filter(pld = self.kwargs['pk']).values('location')

        qs = SupplierFuelFeeRate.objects.with_location().filter(Q(price_active = True),
                                                Q(supplier_fuel_fee__supplier = self.document.supplier),
                                                Q(supplier_fuel_fee__related_pld = self.document),
                                                Q(supplier_fuel_fee__location__in = self.locations),
                                                Q(Q(quantity_band_start = 1) | Q(quantity_band_start = None)),
                                                Q(Q(weight_band_start = 1) | Q(weight_band_start = None))
                                                )

        # Note: datatables will mess with queryset ordering down the line, therefore ordering in get_inital_queryset is
        # useless, we have to use 'initial_order' as above
        # Note: using distinct is of no use too, the column ordering will break

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': False, 'width': '10px'},
        ### Sort helper columns
        {'name': 'supplier_fuel_fee', 'title': 'Fuel Fee ID', 'visible': False,
            'orderable': True},
        ### Sort helper columns
        {'name': 'local_name', 'title': 'Name', 'foreign_field': 'supplier_fuel_fee__local_name', },
        {'name': 'icao_iata', 'title': 'Location', 'placeholder': True},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'supplier_fuel_fee__fuel_fee_category__name'},
        {'name': 'specific_fuel', 'title': 'Fuel', 'lookup_field': '__name__icontains'},
        {'name': 'destination_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
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
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee')\
                   .distinct('destination_type__name','supplier_fuel_fee')
            return qs
        elif 'flight_type' in orders:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee')\
                   .distinct('flight_type__name','supplier_fuel_fee')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']], 'supplier_fuel_fee')\
                   .distinct(orders[0],'supplier_fuel_fee')
            return qs

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
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'category' in column_names:
            return qs.filter(Q(supplier_fuel_fee__fuel_fee_category__name__icontains=search_value)).distinct()

        elif 'pricing_native_amount' in column_names:
            if 'bands apply'.startswith(search_value.lower()):
                return qs.filter(~Q(quantity_band_uom = None) | ~Q(weight_band = None))

            elif 'quantity band applies'.startswith(search_value.lower()):
                return qs.filter(~Q(quantity_band_uom = None), Q(weight_band = None))

            elif 'weight band applies'.startswith(search_value.lower()):
                return qs.filter(Q(quantity_band_uom = None), ~Q(weight_band = None))

            else:
                return qs.filter(Q(Q(quantity_band_uom = None), Q(weight_band = None)),
                                Q(pricing_native_unit__description__icontains=search_value) |
                                Q(pricing_converted_unit__description__icontains=search_value)
                                ).distinct()

        else:
            return qs.filter(search_filters)


    def customize_row(self, row, obj):

        entries = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee = obj.supplier_fuel_fee, price_active = True)

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
        # row['location'] = obj.supplier_fuel_fee.location.airport_details.icao_iata

        view_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_details',
                kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']}),
            button_class='fa-eye',
            button_popup='View Details',
            button_active=self.request.user.has_perm(
                'pricing.p_view'),
            button_modal=False,
            modal_validation=True)

        edit_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_edit',
                kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']}),
            button_class='fa-edit',
            button_popup='Edit',
            button_active=self.request.user.has_perm(
                'pricing.p_update'))

        supersede_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:fuel_pricing_market_documents_supersede_associated_fee',
                kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']}),
            button_class='fa-reply',
            button_popup='Supersede',
            button_active=self.request.user.has_perm(
                'pricing.p_create'))

        archive_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:fuel_pricing_market_documents_associated_fee_archive',
                kwargs={'pk': obj.pk}),
            button_class='fa-trash text-danger',
            button_popup='Archive',
            button_active=self.request.user.has_perm(
                'pricing.p_update'),
            button_modal=True,
            modal_validation=False)

        row['actions'] = view_btn + edit_btn + supersede_btn + archive_btn
        return


class FuelPricingMarketAssociatedFeesSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SupplierFuelFee
    search_values_separator = '+'
    initial_order = [['quantity_band_start', "asc"]]
    permission_required = ['pricing.p_view']


    def get_initial_queryset(self, request=None):
        parent_entry = SupplierFuelFeeRate.objects.get(id=self.kwargs['pk'])
        qs = SupplierFuelFeeRate.objects.filter(supplier_fuel_fee = parent_entry.supplier_fuel_fee, price_active = True)
        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'quantity_band_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'weight_band_start', 'title': 'Bands', 'placeholder': True,},
        {'name': 'pricing_native_amount', 'title': 'Native Pricing', 'placeholder': True},
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True,},
    ]

    def customize_row(self, row, obj):

        for name in row:
            if 'dummy' in name:
                row[name] = ''

        if obj.quantity_band_start:
            row['quantity_band_start'] = f'{obj.quantity_band_uom}: \
                                           {int(obj.quantity_band_start)} - {int(obj.quantity_band_end)}'

        if obj.weight_band_start:
            row['weight_band_start'] = f'{obj.weight_band}: \
                                         {int(obj.weight_band_start)} - {int(obj.weight_band_end)}'

        row['pricing_native_amount'] = obj.get_pricing_datatable_str(for_sublist=True)


# Supplier-Defined Taxes
class FuelPricingMarketSupplierDefinedTaxesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRuleException
    search_values_separator = '+'
    initial_order = [['exception_country', "asc"], ['category', "desc"]]
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_market_updates_document_supplier_defined_tax_list_subtable.html', {
            'object': TaxRuleException.objects.get(id=pk),
            'table_name': 'supplier_defined_tax'
        })

    def get_initial_queryset(self, request=None):
        document = FuelPricingMarketPld.objects.get(id = self.kwargs['pk'])
        locations = document.pld_at_location.all().values('location')
        countries = document.pld_at_location.all().values('location__details__country')

        qs = TaxRuleException.objects.filter(Q(parent_entry = None),
                                             Q(exception_organisation = document.supplier),
                                             Q(deleted_at__isnull = True),
                                             Q(related_pld = document),
                                             Q(Q(exception_airport__in = locations) |
                                             Q(exception_country__in = countries)))

        if document.is_current == False:
            qs = qs.filter(valid_ufn = False)
        else:
            qs = qs.filter(valid_ufn = True)

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Name', 'foreign_field': 'tax__local_name', 'placeholder': True, },
        {'name': 'exception_country', 'title': 'Country', 'visible': False, 'orderable': True},
        {'name': 'location', 'title': 'Location', 'placeholder': True},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'tax__category', 'lookup_field': '__name__icontains'},
        {'name': 'applies_to_fuel', 'title': 'Fuel?'},
        {'name': 'applies_to_fees', 'title': 'Fees?'},
        {'name': 'geographic_flight_type', 'title': 'Destination Type', 'lookup_field': '__name__icontains'},
        {'name': 'applicable_flight_type', 'title': 'Flight Type', 'lookup_field': '__name__icontains'},
        {'name': 'operated_as', 'title': 'Operated As'},
                {'name': 'tax_unit_rate', 'title': 'Rate','placeholder': True},
        {'name': 'valid_from', 'title': 'Valid From', 'lookup_field': 'valid_from__icontains'},
        {'name': 'actions', 'title': '', 'placeholder': True, 'searchable': False, 'orderable': False,
         'className': 'actions_column'},
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'operated_as' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('applies_to_private')
            else:
                qs = qs.order_by('-applies_to_private')
            return qs
        if 'location' in orders:
            if 'ASC' in str(params['orders'][0]):
                qs = qs.order_by('exception_airport__airport_details__icao_code', 'exception_country__name')
            else:
                qs = qs.order_by('-exception_airport__airport_details__icao_code', '-exception_country__name')
            return qs
        else:
            qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
            return qs

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
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
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
                return qs.filter(Q(applies_to_fuel = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = False))
            else:
                return qs.filter(Q(specific_fuel__name__icontains=search_value)
                                 | Q(specific_fuel_cat__name__icontains=search_value))

        elif 'applies_to_fees' in column_names:
            if 'yes'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = True))
            elif 'no'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fees = False))
            else:
                return qs.filter(specific_fee_category__name__icontains = search_value)

        elif 'operated_as' in column_names:
            if 'commercial, private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True),
                                 Q(applies_to_private = True))
            elif 'commercial'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_commercial = True))
            elif 'private'.startswith(search_value.lower()):
                return qs.filter(Q(applies_to_fuel = True))
            else:
                return qs.filter(applies_to_private = False, applies_to_commercial = False)

        elif 'tax_unit_rate' in column_names:
            # istartswith for application methods, because they can contain numbers,
            # which can return the flat rate or percentage
            if 'band(s) applicable'.startswith(search_value.lower()) or 'bands applicable'.startswith(search_value.lower()):
                return qs.filter(Q(parent_entry = None), ~Q(band_1_type = None) | ~Q(band_2_type = None))
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


    def customize_row(self, row, obj):

        related_entries = TaxRuleException.objects.filter(parent_entry = obj.pk)

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

        if obj.applies_to_commercial and obj.applies_to_private:
            row['operated_as'] = 'Commercial, Private'
        else:
            row['operated_as'] = 'Private' if obj.applies_to_private else 'Commercial'


        row['name'] = f'<span class="{add_class}"\>{obj.tax.local_name}</span>'

        if obj.exception_airport:
            row['location'] = obj.exception_airport.airport_details.icao_iata
        else:
            row['location'] = obj.exception_country.name

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

        view_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:fuel_pricing_market_documents_supplier_defined_tax_details',
                                                    kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']}),
                                                button_class='fa-eye',
                                                button_active=self.request.user.has_perm(
                                                    'pricing.p_view'),
                                                button_modal=False,
                                                modal_validation=False)

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:fuel_pricing_market_documents_supplier_defined_tax_edit',
                                                    kwargs={'pk': obj.pk, 'pld': self.kwargs['pk']}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'pricing.p_update'),
                                                button_modal=False,
                                                modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                    'admin:fuel_pricing_market_documents_supplier_defined_tax_archive',
                                                    kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                    'pricing.p_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = view_btn + edit_btn + delete_btn
        return


class FuelPricingMarketSupplierDefinedTaxesSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TaxRuleException
    search_values_separator = '+'
    initial_order = [['band_1_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = TaxRuleException.objects.filter(id=self.kwargs['pk'])
        related_entries = TaxRuleException.objects.filter(parent_entry = self.kwargs['pk'])

        qs = parent_entry.union(related_entries).order_by('band_1_start', 'band_2_start')

        self.disable_queryset_optimization_only = True

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True},
        {'name': 'band_1_start', 'title': 'Bands', 'placeholder': True, },
        {'name': 'band_2_start', 'title': 'Bands', 'placeholder': True,},
        {'name': 'tax_unit_rate', 'title': 'Rate', 'placeholder': True},
        {'name': 'dummy_1', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_2', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_3', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_4', 'title': 'Bands', 'placeholder': True,},
        {'name': 'dummy_5', 'title': 'Bands', 'placeholder': True,},
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


# PLD Tables Section End


# Create / Edit Section Starts
# Fuel Pricing Create
class FuelPricingMarketFuelPricingCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'fuel_pricing_market_updates_fuel_pricing_create.html'
    permission_required = ['pricing.p_create']

    def get(self, request, *args, **kwargs):
        document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pk'])

        new_pricing_formset = NewFuelPricingMarketPricingFormset(form_kwargs={'pld_instance': document},
                                                                 pld_instance = document, context='Create',
                                                                 prefix='new-pricing')

        existing_fuel_pricing_entries = FuelPricingMarket.objects.filter(
                                                            price_active = True,
                                                            supplier_pld_location__in = document.pld_at_location.all())
        new_pld = False
        if request.session.get(f'pld-{document.id}') and not existing_fuel_pricing_entries.exists():
            new_pld = True

        return self.render_to_response({
            'pld_is_new': new_pld,
            'pld_instance': document,
            'fuel_pricing_formset': new_pricing_formset

        })

    def post(self, request, *args, **kwargs):

        expected_forms = int(request.POST.get('new-pricing-TOTAL_FORMS'))
        extra_fields = {i: 0 for i in range(expected_forms)}

        for form_number in extra_fields:
            for key in request.POST:
                if f'band_start-additional-{form_number}-' in key:
                    extra_fields[form_number] += 1

        document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pk'])

        new_pricing_formset = NewFuelPricingMarketPricingFormset(request.POST,
                                                                 form_kwargs={'pld_instance': document},
                                                                 pld_instance = document,
                                                                 extra_fields=extra_fields, context='Create',
                                                                 prefix='new-pricing')

        if all([
            new_pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                # Save new fuel pricing
                for count, form in enumerate(new_pricing_formset):
                    if form.has_changed() and not form.cleaned_data.get('DELETE'):
                        instance = form.save(commit=False)
                        # Get or Create location
                        form_location = form.cleaned_data.get('location')
                        location = FuelPricingMarketPldLocation.objects.get_or_create(pld_id = document.id,
                                                                                    location = form_location)
                        instance.supplier_pld_location = location[0]
                        instance.price_active = True
                        instance.is_latest = True
                        instance.is_published = False
                        instance.updated_by = request.user.person

                        # If we have extra, then we are not even going to care about the main pricing_native_amount
                        if extra_fields[count] != 0:
                            is_first_instance = True

                            for key, value in request.POST.items():
                                if f'-{count}-band_start' in key and value != "":
                                    instance.band_start = value
                                    continue
                                if f'-{count}-band_end' in key and value != "":
                                    instance.band_end = value
                                    continue
                                if f'-{count}-band_pricing' in key:
                                    instance.pricing_native_amount = value

                                    if instance.supplier_exchange_rate:
                                        instance.convert_pricing_amount()

                                    if not is_first_instance:
                                        instance.parent_entry = parent_entry
                                        instance.save()
                                    else:
                                        instance.parent_entry = None
                                        is_first_instance = False
                                        instance.save()

                                        parent_entry = copy.deepcopy(instance)

                                    # DM update must be done when the row has a PK
                                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                    instance.pk = None

                        else:
                            band_pricing = request.POST.get(f'new-pricing-{count}-band_pricing_native_amount')

                            if band_pricing:
                                instance.pricing_native_amount = band_pricing

                            if instance.supplier_exchange_rate:
                                instance.convert_pricing_amount()

                            instance.save()
                            # DM update must be done when the row has a PK
                            instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                        # Update included taxes (M2M, must be done after new instance is saved)
                        # This is done on the main (parent) row only
                        main_instance = instance if instance.pk else parent_entry
                        inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                        cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                        main_instance.inclusive_taxes = inclusive_taxes, cascade_to_fees

                messages.success(request, 'Fuel Pricing created successfully')

                if request.session.get(f'pld-{document.id}'):
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_documents_associated_fees_create_page',
                                                            kwargs={'pk': document.id}))
                else:
                    return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                            kwargs={'pk': document.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            existing_fuel_pricing_entries = FuelPricingMarket.objects.filter(
                                                            price_active = True,
                                                            supplier_pld_location__in = document.pld_at_location.all())

            new_pld = False
            if request.session.get(f'pld-{document.id}') and not existing_fuel_pricing_entries.exists():
                new_pld = True

            return self.render_to_response({
                'pld_is_new': new_pld,
                'pld_instance': document,
                'fuel_pricing_formset': new_pricing_formset
            })


# Fuel Pricing Edit
class FuelPricingMarketFuelPricingEditView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'fuel_pricing_market_updates_fuel_pricing_edit.html'
    permission_required = ['pricing.p_create']

    def get(self, request, *args, **kwargs):
        document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])
        entry = FuelPricingMarket.objects.get(id = self.kwargs['pk'])
        related_entries = FuelPricingMarket.objects.filter(parent_entry = self.kwargs['pk'], price_active = True)

        pricing_formset = FuelPricingMarketPricingFormset(form_kwargs={'context': 'Edit', 'entry':entry},
                                                          prefix='new-pricing', context='Edit', entry=entry,
                                                          related_entries=related_entries)

        return self.render_to_response({
            'pld_instance': document,
            'fuel_pricing_formset': pricing_formset

        })

    def post(self, request, *args, **kwargs):

        extra_fields = {0: 0}
        for key in request.POST:
            if f'band_start-additional' in key:
                extra_fields[0] += 1

        document = FuelPricingMarketPld.objects.get(pk=self.kwargs['pld'])

        entry = FuelPricingMarket.objects.get(id = self.kwargs['pk'])
        related_entries = FuelPricingMarket.objects.filter(price_active = True, parent_entry = self.kwargs['pk'])\
                                                   .order_by('band_start')

        pricing_formset = FuelPricingMarketPricingFormset(
                                                request.POST,
                                                form_kwargs={'pld_instance': document,'context': 'Edit','entry': entry},
                                                context="Edit", entry=entry, extra_fields=extra_fields,
                                                related_entries=related_entries,
                                                prefix='new-pricing')

        if all([
            pricing_formset.is_valid()
        ]):
            with transaction.atomic():

                has_new_bands = False
                location = entry.supplier_pld_location

                for field in request.POST:
                    if 'additional' in field:
                        has_new_bands = True

                for count, form in enumerate(pricing_formset):
                    instance = form.save(commit=False)
                    instance.updated_by = request.user.person
                    instance.supplier_pld_location = location
                    band_pricing = request.POST.get(f'new-pricing-{count}-band_pricing_native_amount')
                    existing_entry = 0

                    if form.cleaned_data.get('specific_hookup_method') is None:
                        instance.specific_hookup_method = None

                    # Update included taxes and delivery methods for main entry (M2M relations)
                    inclusive_taxes = dict(request.POST).get(f'new-pricing-{count}-inclusive_taxes', [])
                    cascade_to_fees = request.POST.get(f'new-pricing-{count}-cascade_to_fees', False)
                    instance.inclusive_taxes = inclusive_taxes, cascade_to_fees
                    instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))

                    if instance.supplier_exchange_rate:
                        instance.convert_pricing_amount()

                    if band_pricing:
                        instance.pricing_native_amount = band_pricing

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
                            if f'amount-additional' in key:
                                instance.pricing_native_amount = value
                                instance.parent_entry = parent_entry

                                if instance.supplier_exchange_rate:
                                    instance.convert_pricing_amount()

                                if existing_entry < related_entries.count():
                                    instance.pk = related_entries[existing_entry].pk
                                    instance.save()
                                    existing_entry += 1
                                else:
                                    instance.save()

                                instance.delivery_methods.set(form.cleaned_data.get('delivery_methods'))
                                instance.pk = None

                    # Delete the remaining
                    # I assume it is OK to delete in this case, as to not litter the database with wrongful entries
                    # and only set price as inactive on supersede as to preserve the history
                    while existing_entry < related_entries.count():
                        related_entries[existing_entry].delete()
                        existing_entry += 1

                messages.success(request, 'Fuel Pricing updated successfully')

                return HttpResponseRedirect(reverse_lazy('admin:fuel_pricing_market_document_details',
                                                            kwargs={'pk': document.id}))
        else:
            messages.error(request, 'Error found in submitted form')

            return self.render_to_response({
                'pld_instance': document,
                'fuel_pricing_formset': pricing_formset
            })


# Fuel Pricing Details
class FuelPricingMarketFuelPricingDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'fuel_pricing_market_updates_fuel_pricing_details.html'
    model = FuelPricingMarket
    context_object_name = 'entry'
    permission_required = ['pricing.p_view']

    def get_queryset(self):
        qs = FuelPricingMarket.objects.filter(Q(id = self.kwargs['pk']))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_entries'] = FuelPricingMarket.objects.filter(parent_entry = self.kwargs['pk'],
                                                                      price_active = True).order_by('band_start')
        return context


# Archive (Delete) Fuel Pricing
class FuelPricingMarketFuelPricingArchiveView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = FuelPricingMarket
    form_class = ConfirmationForm
    success_message = 'Pricing entry archived successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:fuel_pricing_market_document_details',
                            kwargs={'pk': self.entry.supplier_pld_location.pld_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Archive Pricing Entry',
            'text': f'Are you sure you want to archive this pricing entry?',
            'icon': 'fa-trash',
            'action_button_text': 'Archive',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':

            main_entries = FuelPricingMarket.objects.filter(id = self.kwargs['pk'])
            related_entries = FuelPricingMarket.objects.filter(parent_entry = self.kwargs['pk'])
            all_entries = main_entries.union(related_entries)

            time_now = datetime.now()

            # Not going to modify the valid_to date here (that can hold the reference of an initial validity range)
            for entry in all_entries:
                entry.price_active = False
                entry.is_published = False
                entry.deleted_at = time_now
                entry.updated_by = self.request.user.person
                entry.save()

            self.entry = entry

        return super().form_valid(form)


#########################
# Billable Organisations
#########################

class FuelPricingMarketPldBillableOrganisationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['pricing.p_view']

    pld = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.pld = get_object_or_404(FuelPricingMarketPld, pk=self.kwargs['pk'])

    def get_initial_queryset(self, request=None):
        return self.model.objects.billable_orgs_for_pld(self.pld)

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False,
         'orderable': False, 'width': '10px'},
        {'name': 'details', 'title': 'Billable Organisation', 'searchable': False,
         'placeholder': True, 'className': 'url_source_col single_cell_link',},
        {'name': 'locations', 'title': 'Locations', 'orderable': False, 'searchable': False,
         'placeholder': True, },
    ]

    def customize_row(self, row, obj):
        row['details'] = f'<span data-url={obj.get_absolute_url()}>{obj.details.registered_and_trading_name}</span>'
        row['locations'] = self.pld.locations_billed_by_org_str(obj)


class FuelPricingMarketPldBillableOrganisationsEditView(AdminPermissionsMixin, BSModalFormView):
    error_css_class = 'is-invalid'
    template_name = 'pricing_pages_includes/_pricing_market_updates_billable_organisations_modal.html'
    form_class = FuelPricingMarketPldBillableOrganisationsForm
    success_message = 'Billable organisations updated successfully'
    permission_required = ['pricing.p_update']

    formset = None
    pld = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.pld = get_object_or_404(FuelPricingMarketPld, pk=self.kwargs['pk'])

        if self.request.method == 'POST':
            self.formset = FuelPricingMarketPldBillableOrganisationsFormset(
                self.request.POST, prefix='billable_org')
        else:
            self.formset = FuelPricingMarketPldBillableOrganisationsFormset(
                queryset=FuelPricingMarketPldLocation.objects.filter(pld=self.pld), prefix='billable_org')

        # Pass the request to all forms
        for form in self.formset:
            form.request = request

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = self.formset

        metacontext = {
            'title': 'Edit Billable Organisations',
            'icon': 'fa-money-bill',
        }

        context['metacontext'] = metacontext
        return context

    def post(self, request, *args, **kwargs):
        if all([
            self.formset.is_valid()
        ]):
            self.formset.save()

            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(**kwargs))

