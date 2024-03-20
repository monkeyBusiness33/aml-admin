import json
from datetime import datetime, timedelta, timezone

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Case, CharField, ExpressionWrapper, F, Q, Value, When
from django.db.models.functions import Concat
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.templatetags.static import static
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView, BSModalUpdateView
from bootstrap_modal_forms.mixins import PassRequestMixin
from bootstrap_modal_forms.mixins import is_ajax

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_badge, get_datatable_actions_button
from organisation.models import OrganisationDocument
from pricing.utils import get_datatable_agreement_locations_list
from supplier.utils import get_datatable_agreement_status_badge
from supplier.forms import FuelAgreementDetailsForm, FuelAgreementExtendForm, FuelAgreementVoidForm
from supplier.models import FuelAgreement
from user.mixins import AdminPermissionsMixin


class FuelAgreementsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreement
    initial_order = [["is_active", "desc"], ["end_date", "asc"], ]
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'supplier_name', 'title': 'Supplier Name', 'visible': True,
         'sort_field': 'namestring', 'className': 'organisation_reg_name'},
        {'name': 'locations', 'title': 'Location(s)', 'className': 'location', 'orderable': False,
         'placeholder': True},
        {'name': 'start_date', 'title': 'Start Date', 'visible': True,
         'searchable': False},
        {'name': 'end_date', 'title': 'End Date', 'visible': True,
         'searchable': False},
        {'name': 'is_active', 'title': 'Active?', 'visible': True,
         'searchable': False},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False, 'className': 'organisation_status'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '120px', 'className': 'actions', },
    ]

    def get_initial_queryset(self, request=None):
        '''
        Annotate the objects with a name string for sorting (trading name goes first
        in this column, but if absent, only registered name is used instead)
        '''
        qs = super().get_initial_queryset(request)

        qs = qs.annotate(
            namestring=Case(
                When(supplier__details__trading_name__isnull=False, then=Concat(
                    'supplier__details__trading_name',
                    Value(' ('),
                    'supplier__details__registered_name',
                    output_field=CharField())),
                default=F('supplier__details__registered_name')
            )
        )

        return qs

    def filter_queryset_all_columns(self, search_value, qs):
        searchable_columns = [c['name'] for c in self.column_specs if c['searchable']]
        searchable_columns.remove('locations')
        return self._filter_queryset(searchable_columns, search_value, qs, True)

    def filter_queryset(self, params, qs):
        qs = self.filter_queryset_by_date_range(params.get('date_from', None), params.get('date_to', None), qs)

        if 'search_value' in params:
            search_value = params['search_value']
            qs = qs.filter(
                Q(pricing_formulae__location__airport_details__icao_code__istartswith=search_value) |
                Q(pricing_formulae__location__airport_details__iata_code__istartswith=search_value) |
                Q(pricing_manual__location__airport_details__icao_code__istartswith=search_value) |
                Q(pricing_manual__location__airport_details__iata_code__istartswith=search_value)
            ).union(self.filter_queryset_all_columns(params['search_value'], qs))

        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_value = column_link.search_value

                if column_link.name == 'locations':
                    qs = qs.filter(
                        Q(pricing_formulae__location__airport_details__icao_code__istartswith=search_value) |
                        Q(pricing_formulae__location__airport_details__iata_code__istartswith=search_value) |
                        Q(pricing_manual__location__airport_details__icao_code__istartswith=search_value) |
                        Q(pricing_manual__location__airport_details__iata_code__istartswith=search_value)
                    ).distinct()
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def customize_row(self, row, obj):
        row['supplier_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.supplier_name}</span>'
        row['locations'] = get_datatable_agreement_locations_list(obj)
        row['start_date'] = obj.start_date.strftime("%Y-%m-%d") if obj.start_date else None
        row['end_date'] = 'Until Further Notice' if obj.valid_ufn else obj.end_date.date()
        row['is_active'] = obj.active_badge

        status_badge = get_datatable_agreement_status_badge(obj)

        row['status'] = status_badge + (get_datatable_badge(badge_text='Expiring Soon',
                                                            badge_class='bg-danger datatable-badge-normal',
                                                            tooltip_text='Agreement Expiring Soon')
                                        if obj.is_expiring else '')

        publish_btn_url = f"admin:fuel_agreement_{'unpublish' if obj.is_published else 'publish'}"

        if obj.voided_at is None:
            publish_btn = get_datatable_actions_button(button_text='Unpublish' if obj.is_published else 'Publish',
                                                       button_url=reverse_lazy(
                                                           publish_btn_url, kwargs={
                                                               'pk': obj.pk
                                                           }),
                                                       button_class='btn-outline-primary',
                                                       button_icon='fa-times' if obj.is_published else 'fa-check',
                                                       button_active=self.request.user.has_perm('pricing.p_publish'),
                                                       button_modal=True,
                                                       modal_validation=False)
            row['actions'] = publish_btn
        else:
            row['actions'] = ''

        return


class FuelAgreementsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        header_buttons_list = [{
            'button_text': 'New Fuel Agreement',
            'button_icon': 'fa-plus',
            'button_url': reverse('admin:fuel_agreement_create'),
            'button_modal': False,
            'button_perm': self.request.user.has_perm('pricing.p_create'),
        }]

        metacontext = {
            'title': 'Supplier Fuel Agreements',
            'page_id': 'supplier_fuel_agreements_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:fuel_agreements_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
        }

        context['metacontext'] = metacontext
        return context


class FuelAgreementDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'fuel_agreement.html'
    model = FuelAgreement
    context_object_name = 'agreement'
    permission_required = ['pricing.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # When loading the page without 'from_creation' in query string, the agreement is no longer considered new
        if 'from_creation' not in self.request.GET:
            self.request.session.pop(f'agreement-{self.object.pk}', None)

        metacontext = {
            'pricing_type_select_modal_id': 'pricing_type_select_modal_id',
            'modal_title': 'Select Fuel Pricing Type',
            'modal_text': 'Select fuel pricing type to be created for this newly created agreement.',
            'modal_id': 'pricing_type_select_modal',
            'modal_icon': 'fa-plus',
            'modal_cancel_btn_id': 'modal_cancel_btn_id',
            'modal_cancel_btn_text': 'Skip Pricing Creation',
            'modal_action_btn_0_id': 'modal_formula_btn_id',
            'modal_action_btn_0_url': reverse_lazy('admin:agreement_formula_pricing_create',
                                                   kwargs={'agreement_pk': self.object.pk}),
            'modal_action_btn_0_text': 'Create Formula Pricing',
            'modal_action_btn_1_id': 'modal_discount_btn_id',
            'modal_action_btn_1_url': reverse_lazy('admin:agreement_discount_pricing_create',
                                                   kwargs={'agreement_pk': self.object.pk}),
            'modal_action_btn_1_text': 'Create Discount Pricing',
        }

        context['metacontext'] = metacontext
        context['has_associated_fees'] = self.object.display_fees.exists()
        context['has_associated_taxes'] = self.object.display_supplier_taxes.exists()
        return context

class FuelAgreementCreateView(AdminPermissionsMixin, PassRequestMixin, SuccessMessageMixin, CreateView):
    template_name = 'fuel_agreement_create.html'
    model = FuelAgreement
    form_class = FuelAgreementDetailsForm
    context_object_name = 'agreement'
    success_message = 'Agreement created successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return f"{reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.object.pk})}?from_creation=1"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Create Fuel Agreement',
            'form_id': 'create_fuel_agreement',
            'action_button_text': 'Save and Continue',
            'mode': 'create',
        }

        context['metacontext'] = metacontext
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({'mode': 'create'})

        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = getattr(self.request.user, 'person')
        form_data = form.cleaned_data

        # Parse end date / UFN
        if form_data['valid_ufn']:
            form.instance.end_date = None
        else:
            form.instance.end_date = form_data['end_date']

        # Parse payment terms
        payment_terms_count = form_data['payment_terms_unit_count']
        payment_terms_unit = form_data['payment_terms_time_unit']

        if payment_terms_unit == 'D':
            form.instance.payment_terms_days = payment_terms_count
            form.instance.payment_terms_months = None
        else:
            form.instance.payment_terms_days = None
            form.instance.payment_terms_months = payment_terms_count

        form.instance.update_active_status_based_on_date()

        # Parse source document
        doc_name = form_data['source_doc_name']
        doc_file = self.request.FILES.get('source_doc_file', None) or getattr(form.instance.document, 'file', None)
        doc_description = form_data['source_doc_description']

        if doc_name and doc_file:
            doc = OrganisationDocument.objects.create(
                name=doc_name,
                file=doc_file,
                description=doc_description,
                type_id=19,
                organisation=form.instance.supplier
            )
            form.instance.document = doc

        is_new_agreement = form.instance.pk is None
        redirect_url = super().form_valid(form)

        if is_new_agreement:
            self.request.session[f'agreement-{form.instance.pk}'] = 'new'

        return redirect_url



class FuelAgreementEditView(AdminPermissionsMixin, PassRequestMixin, SuccessMessageMixin, UpdateView):
    template_name = 'fuel_agreement_create.html'
    model = FuelAgreement
    form_class = FuelAgreementDetailsForm
    context_object_name = 'agreement'
    success_message = 'Agreement updated successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.object.pk})

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Edit Fuel Agreement',
            'form_id': 'edit_fuel_agreement',
            'action_button_text': 'Save Changes',
            'mode': 'edit',
        }

        context['metacontext'] = metacontext
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mode': 'edit'})

        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = getattr(self.request.user, 'person')
        form_data = form.cleaned_data

        # Parse end date / UFN
        if form_data['valid_ufn']:
            form.instance.end_date = None
        else:
            form.instance.end_date = form_data['end_date']

        # Parse payment terms
        payment_terms_count = form_data['payment_terms_unit_count']
        payment_terms_unit = form_data['payment_terms_time_unit']

        if payment_terms_unit == 'D':
            form.instance.payment_terms_days = payment_terms_count
            form.instance.payment_terms_months = None
        else:
            form.instance.payment_terms_days = None
            form.instance.payment_terms_months = payment_terms_count

        # Parse source document
        doc_name = form_data['source_doc_name']
        doc_file = self.request.FILES.get('source_doc_file', None) or getattr(form.instance.document, 'file', None)
        doc_description = form_data['source_doc_description']

        if doc_name and doc_file:
            doc, _ = OrganisationDocument.objects.update_or_create(
                pk=getattr(form.instance.document, 'pk', None),
                defaults={
                    'name': doc_name,
                    'file': doc_file,
                    'description': doc_description,
                    'type_id': 19,
                    'organisation': form.instance.supplier
                }
            )
            form.instance.document = doc

        return super().form_valid(form)


class FuelAgreementSupersedeView(PassRequestMixin, SuccessMessageMixin, CreateView):
    template_name = 'fuel_agreement_create.html'
    model = FuelAgreement
    form_class = FuelAgreementDetailsForm
    context_object_name = 'agreement'
    success_message = 'Agreement superseded successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return reverse_lazy('admin:agreement_pricing_supersede', kwargs={'pk': self.object.pk})

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.old_agreement = get_object_or_404(FuelAgreement, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Supersede Fuel Agreement',
            'form_id': 'supersede_fuel_agreement',
            'action_button_text': 'Save and Continue',
            'mode': 'supersede',
        }

        context['old_agreement'] = self.old_agreement
        context['metacontext'] = metacontext
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({
            'mode': 'supersede',
            'old_agreement': FuelAgreement.objects.get(pk=self.kwargs['pk'])
        })

        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = getattr(self.request.user, 'person')
        form_data = form.cleaned_data

        # Parse end date / UFN
        if form_data['valid_ufn']:
            form.instance.end_date = None
        else:
            form.instance.end_date = form_data['end_date']

        # Parse payment terms
        payment_terms_count = form_data['payment_terms_unit_count']
        payment_terms_unit = form_data['payment_terms_time_unit']

        if payment_terms_unit == 'D':
            form.instance.payment_terms_days = payment_terms_count
            form.instance.payment_terms_months = None
        else:
            form.instance.payment_terms_days = None
            form.instance.payment_terms_months = payment_terms_count

        form.instance.update_active_status_based_on_date()

        # Parse source document
        doc_name = form_data['source_doc_name']
        doc_file = self.request.FILES.get('source_doc_file', None) or getattr(form.instance.document, 'file', None)
        doc_description = form_data['source_doc_description']

        if doc_name and doc_file:
            doc = OrganisationDocument.objects.create(
                name=doc_name,
                file=doc_file,
                description=doc_description,
                type_id=19,
                organisation=form.instance.supplier
            )
            form.instance.document = doc

        # Update end date of old agreement to end before new one starts
        if self.old_agreement.valid_ufn or self.old_agreement.end_date.date() >= form.instance.start_date:
            self.old_agreement.end_date = form.instance.start_date - timedelta(days=1)
            self.old_agreement.valid_ufn = False
            self.old_agreement.update_active_status_based_on_date()

        self.old_agreement.superseded_by = form.instance
        response = super().form_valid(form)
        self.old_agreement.save()

        return response


class FuelAgreementExtendView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = '_fuel_agreement_extend_modal.html'
    model = FuelAgreement
    form_class = FuelAgreementExtendForm
    success_message = 'The agreement was extended successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.object.pk})

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'form_id': 'id_extend_form',
            'title': 'Extend Fuel Agreement',
            'text': f'Please select a new validity date for this agreement.',
            'icon': 'fa-calendar-plus',
            'action_button_text': 'Confirm',
        }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            form_data = form.cleaned_data

            if form_data['valid_ufn']:
                form.instance.valid_ufn = True
                form.instance.end_date = None
            else:
                form.instance.valid_ufn = False
                form.instance.end_date = form_data['end_date']

            form.instance.update_active_status_based_on_date()
            form.instance.save()

        return super().form_valid(form)

class FuelAgreementVoidView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = '_fuel_agreement_void_modal.html'
    model = FuelAgreement
    form_class = FuelAgreementVoidForm
    success_message = 'The agreement was voided successfully'
    permission_required = ['pricing.p_update']

    def get_object(self):
        obj = get_object_or_404(FuelAgreement, pk=self.kwargs['pk'])
        return obj

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'form_id': 'id_void_form',
            'title': 'Void a Fuel Agreement',
            'text': f'Please select a new validity end date for this agreement'
                    f' (between {"today" if self.object.has_started else "start date"}'
                    f' and current end date).',
            'icon': 'fa-times',
            'action_button_text': 'Confirm',
            'js_scripts': [
                static('js/fuel_agreement_void_modal.js')
            ],
        }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form, *args, **kwargs):
        form_data = form.cleaned_data

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            obj = self.get_object()
            timestamp = datetime.now(timezone.utc)
            obj.end_date = form_data['end_date'] if not form_data['void_immediately'] else timestamp
            obj.valid_ufn = False
            obj.is_published = False
            obj.voided_at = timestamp
            obj.update_active_status_based_on_date()
            obj.save()

        return HttpResponseRedirect(self.get_success_url())


class FuelAgreementDeleteDocumentView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationDocument
    form_class = ConfirmationForm
    success_message = 'Document deleted successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={
            'pk': self.object.fuel_agreement_where_source_document.first().pk
        })

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Delete Document',
            'text': f'Are you sure you want to delete this document?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context


class FuelAgreementPublishView(AdminPermissionsMixin, BSModalFormView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelAgreement
    form_class = ConfirmationForm
    permission_required = ['pricing.p_publish']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        instance = self.model.objects.get(pk=self.kwargs['pk'])

        if instance.is_published:
            metacontext = {
                'title': 'Unpublish Fuel Agreement',
                'text': f'Are you sure you want to hide this fuel agreement?',
                'icon': 'fa-minus',
                'action_button_text': 'Unpublish',
                'action_button_class': 'btn-success',
            }
        else:
            metacontext = {
                'title': 'Publish Fuel Agreement',
                'text': f'Are you sure you want to publish this fuel agreement?',
                'icon': 'fa-plus',
                'action_button_text': 'Publish',
                'action_button_class': 'btn-success',
            }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form):
        instance = self.model.objects.get(pk=self.kwargs['pk'])

        if instance.is_published:
            instance.is_published = False
            messages.success(self.request, 'Fuel Agreement has been hidden')
        else:
            instance.is_published = True
            messages.success(self.request, 'Fuel Agreement has been published')

        instance.save()

        return super().form_valid(form)
