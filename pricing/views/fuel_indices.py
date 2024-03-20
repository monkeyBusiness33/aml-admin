import json
from datetime import timedelta
from ajax_datatable.views import AjaxDatatableView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import CharField, ExpressionWrapper, F, Q
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalFormView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax
from core.forms import ConfirmationForm
from core.utils.custom_query_expressions import CommaSeparatedDecimal
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_badge, \
    get_datatable_badge_from_status
from user.mixins import AdminPermissionsMixin
from ..forms.fuel_indices import FuelIndexDetailsForm, FuelIndexPricingDetailsForm
from ..models import FuelAgreementPricingFormula, FuelIndex, FuelIndexDetails, FuelIndexPricing


class FuelIndicesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelIndex
    initial_order = [["is_active", "desc"], ["full_name", "asc"], ]
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'full_name', 'title': 'Index Name', 'visible': True, 'sort_field': 'full_name',
         'className': 'url_source_col'},
        {'name': 'is_active', 'title': 'Active?', 'visible': True, 'searchable': False},
        {'name': 'status', 'title': 'status', 'visible': True, 'searchable': False,
         'orderable': True},
        # {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
        #  'orderable': False, 'className': 'actions' },
    ]

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_status()

    def filter_queryset(self, params, qs):
        if 'search_value' in params:
            qs = qs.filter(Q(name__icontains=params['search_value']) |
                           Q(provider__details__trading_name__icontains=params['search_value']) |
                           Q(provider__details__registered_name__icontains=params['search_value']))

        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                if column_link.name == 'provider':
                    qs = qs.filter(Q(provider__details__trading_name__icontains=column_link.search_value) |
                                   Q(provider__details__registered_name__icontains=column_link.search_value))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def customize_row(self, row, obj):
        row['full_name'] = f'<span data-url="{obj.get_absolute_url()}">{row["full_name"]}</span>'
        row['provider'] = f'<span data-url="{obj.provider.get_absolute_url()}">' \
                          f'{obj.provider.full_repr}</span>'
        row['is_active'] = obj.active_badge
        row['status'] = get_datatable_badge_from_status(status=obj.full_status)

        # delete_btn = get_datatable_actions_button(button_text='',
        #                                           button_url=reverse_lazy(
        #                                               'admin:fuel_index_delete', kwargs={
        #                                                   'pk': obj.pk
        #                                               }),
        #                                           button_class='fa-trash text-danger',
        #                                           button_active=self.request.user.has_perm('pricing.p_update'),
        #                                           button_modal=True,
        #                                           modal_validation=False)
        #
        # row['actions'] = delete_btn


class FuelPricingIndicesListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            # {'button_text': 'Add Fuel Pricing Index',
            #  'button_icon': 'fa-plus',
            #  'button_url': reverse('admin:fuel_index_create'),
            #  'button_modal': True,
            #  'button_perm': self.request.user.has_perm('pricing.p_create')},
        ]

        metacontext = {
            'title': 'Fuel Pricing Indices',
            'page_id': 'fuel_pricing_indices_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:fuel_indices_ajax',
            'header_buttons_list': json.dumps(header_buttons_list),
        }

        context['metacontext'] = metacontext
        return context


class FuelIndexCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndex
    form_class = FuelIndexDetailsForm
    success_url = reverse_lazy('admin:fuel_pricing_indices')
    success_message = 'Fuel Index created successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create Fuel Index',
            'icon': 'fa-gas-pump',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        instance = form.save()

        # Save associated fuel index detail flags
        instance.index_period = data['index_period']
        instance.index_price = data['index_price']

        return super().form_valid(form)


class FuelIndexDetailsView(AdminPermissionsMixin, TemplateView):
    template_name = 'fuel_index_details.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fuel_index = FuelIndex.objects.get(pk=self.kwargs['pk'])
        context['index'] = fuel_index

        metacontext = {
        }

        context['metacontext'] = metacontext
        return context


class FuelIndexEditView(AdminPermissionsMixin, BSModalUpdateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndex
    form_class = FuelIndexDetailsForm
    success_message = 'Fuel Index updated successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Fuel Index',
            'icon': 'fa-gas-pump',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        data = form.cleaned_data

        # Save associated fuel index detail flags
        self.object.index_period = data['index_period']
        self.object.index_price = data['index_price']

        return super().form_valid(form)


class FuelIndexDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = FuelIndex
    form_class = ConfirmationForm
    success_message = 'Fuel Index has been deleted'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Fuel Index',
            'text': f'Are you sure you want to delete this fuel index?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context


class FuelIndexPricingListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelIndexPricing
    initial_order = [["is_active", "desc"], ["valid_to", "desc"], ]
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'fuel_index_details', 'title': 'Index Pricing Details',
         'visible': True, 'searchable': True, 'orderable': True, },
        {'name': 'price', 'title': 'Price', 'visible': True, 'searchable': False, 'orderable': True, },
        {'name': 'is_primary', 'title': 'Primary?', 'visible': True, 'searchable': False},
        {'name': 'is_active', 'title': 'Active?', 'visible': True, 'searchable': False, },
        {'name': 'validity', 'title': 'Validity', 'visible': True, 'searchable': False, 'orderable': True,
         'sort_field': 'valid_to', },
        {'name': 'valid_to', 'title': '', 'visible': False, 'searchable': True, 'orderable': True, },
        {'name': 'source_organisation', 'title': 'Source Organisation', 'visible': True,
         'searchable': True, 'orderable': True, },
        {'name': 'status', 'title': 'Status', 'visible': True, 'searchable': False, 'orderable': False, },
        {'name': 'updated_at', 'title': 'Updated', 'visible': True, 'searchable': False, 'orderable': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'actions'},
    ]

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': self.model.objects.get(id=pk),
            'table_name': 'fuel_index_pricing_sublist',
            'table_url': reverse_lazy('admin:fuel_index_pricing_sublist_ajax', kwargs={
                'index_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        """
        Get the latest entry for each combination of details and source org.
        The remaining prices will be available on row expansion.
        """
        return self.model.objects.with_structure_details().latest_only().filter(
            fuel_index_details__fuel_index__pk=self.kwargs['pk']
        ).annotate(
            price_str=ExpressionWrapper(
                CommaSeparatedDecimal(F('price')),
                output_field=CharField())
        )

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_val = column_link.search_value
                if column_link.name == 'source_organisation':
                    qs = qs.filter(Q(source_organisation__details__registered_name__icontains=search_val)
                                   | Q(source_organisation__details__trading_name__icontains=search_val))
                if column_link.name == 'fuel_index_details':
                    qs = qs.filter(Q(structure_str__icontains=search_val)
                                   | Q(structure_str__icontains=search_val))

        return qs

    def customize_row(self, row, obj):
        add_class = 'has_children' if obj.pricing_entry_count > 1 else ''
        row['fuel_index_details'] = f'<span class="{add_class}"\>{obj.fuel_index_details.structure_description}</span>'
        row['price'] = obj.get_pricing_datatable_str()
        row['is_primary'] = obj.primary_badge
        row['is_active'] = obj.active_badge
        row['status'] = get_datatable_badge(badge_text=f"{'Published' if obj.is_published else 'Unpublished'}",
                                            badge_class=f"{'bg-success' if obj.is_published else 'bg-warning'}")
        row['source_organisation'] = obj.source_organisation.details.registered_and_trading_name
        row['updated_at'] = f"{obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')} ({obj.updated_by.initials})"

        edit_btn = get_datatable_actions_button(
            button_text=f'Edit',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_edit', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-edit',
            button_active=self.request.user.has_perm('pricing.p_update'),
            button_modal=True) if not obj.has_expired and not obj.is_superseded else ''

        delete_btn = get_datatable_actions_button(
            button_text='Delete',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_delete', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-danger',
            button_icon='fa-trash',
            button_active=self.request.user.has_perm('pricing.p_update'),
            button_modal=True,
            modal_validation=False) if not obj.has_expired and not obj.is_superseded else ''

        publish_btn_url = f"admin:fuel_index_pricing_{'unpublish' if obj.is_published else 'publish'}"
        publish_btn = get_datatable_actions_button(
            button_text='Unpublish' if obj.is_published else 'Publish',
            button_url=reverse_lazy(
                publish_btn_url, kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-times' if obj.is_published else 'fa-check',
            button_active=self.request.user.has_perm('pricing.p_publish'),
            button_modal=True,
            modal_validation=False) if not obj.has_expired and not obj.is_superseded else ''

        supersede_btn = get_datatable_actions_button(
            button_text='Supersede',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_supersede', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-reply',
            button_active=self.request.user.has_perm('pricing.p_create'),
            button_modal=True,
            modal_validation=True) if not obj.is_superseded else ''
        row['actions'] = edit_btn + delete_btn + publish_btn + supersede_btn


class FuelIndexPricingSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelIndexPricing
    initial_order = [["valid_to", "desc"], ]
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'fuel_index_details', 'title': 'Index Pricing Details',
         'visible': True, 'searchable': True, 'orderable': True, },
        {'name': 'price', 'title': 'Price', 'visible': True, 'searchable': False, 'orderable': True, },
        {'name': 'is_primary', 'title': 'Primary?', 'visible': True, 'searchable': False},
        {'name': 'is_active', 'title': 'Active?', 'visible': True, 'searchable': False, },
        {'name': 'validity', 'title': 'Validity', 'visible': True, 'searchable': False, 'orderable': True,
         'sort_field': 'valid_to', },
        {'name': 'valid_to', 'title': '', 'visible': False, 'searchable': True, 'orderable': True, },
        {'name': 'source_organisation', 'title': 'Source Organisation', 'visible': True,
         'searchable': True, 'orderable': True, },
        {'name': 'status', 'title': 'Status', 'visible': True, 'searchable': False, 'orderable': False, },
        {'name': 'updated_at', 'title': 'Updated', 'visible': True, 'searchable': False, 'orderable': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'actions'},
    ]

    def get_initial_queryset(self, request=None):
        parent_entry = self.model.objects.get(id=self.kwargs['pk'])

        return self.model.objects.filter(
            Q(fuel_index_details=parent_entry.fuel_index_details)
            & Q(source_organisation=parent_entry.source_organisation)
            & ~Q(pk=self.kwargs['pk'])
        )

    def filter_queryset(self, params, qs):
        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                search_val = column_link.search_value
                if column_link.name == 'source_organisation':
                    qs = qs.filter(Q(source_organisation__details__registered_name__icontains=search_val)
                                   | Q(source_organisation__details__trading_name__icontains=search_val))
                if column_link.name == 'fuel_index_details':
                    qs = qs.filter(Q(structure_str__icontains=search_val)
                                   | Q(structure_str__icontains=search_val))

        return qs

    def customize_row(self, row, obj):
        row['fuel_index_details'] = obj.fuel_index_details.structure_description
        row['price'] = obj.get_pricing_datatable_str()
        row['is_primary'] = obj.primary_badge
        row['is_active'] = obj.active_badge
        row['status'] = get_datatable_badge(badge_text=f"{'Published' if obj.is_published else 'Unpublished'}",
                                            badge_class=f"{'bg-success' if obj.is_published else 'bg-warning'}")
        row['source_organisation'] = obj.source_organisation.details.registered_and_trading_name
        row['updated_at'] = f"{obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')} ({obj.updated_by.initials})"

        edit_btn = get_datatable_actions_button(
            button_text='Edit',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_edit', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-edit',
            button_active=self.request.user.has_perm('pricing.p_update'),
            button_modal=True) if not obj.has_expired and not obj.is_superseded else ''

        delete_btn = get_datatable_actions_button(
            button_text='Delete',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_delete', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-danger',
            button_icon='fa-trash',
            button_active=self.request.user.has_perm('pricing.p_update'),
            button_modal=True,
            modal_validation=False) if not obj.has_expired and not obj.is_superseded else ''

        publish_btn_url = f"admin:fuel_index_pricing_{'unpublish' if obj.is_published else 'publish'}"
        publish_btn = get_datatable_actions_button(
            button_text='Unpublish' if obj.is_published else 'Publish',
            button_url=reverse_lazy(
                publish_btn_url, kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-times' if obj.is_published else 'fa-check',
            button_active=self.request.user.has_perm('pricing.p_publish'),
            button_modal=True,
            modal_validation=False) if not obj.has_expired and not obj.is_superseded else ''

        supersede_btn = get_datatable_actions_button(
            button_text='Supersede',
            button_url=reverse_lazy(
                'admin:fuel_index_pricing_supersede', kwargs={
                    'pk': obj.pk
                }),
            button_class='btn-outline-primary',
            button_icon='fa-reply',
            button_active=self.request.user.has_perm('pricing.p_create'),
            button_modal=True,
            modal_validation=True) if not obj.is_superseded else ''
        row['actions'] = edit_btn + delete_btn + publish_btn + supersede_btn


class FuelIndexPricingCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndexPricing
    form_class = FuelIndexPricingDetailsForm
    success_message = 'Fuel Index Pricing created successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'fuel_index': FuelIndex.objects.get(pk=self.kwargs['index_pk']),
            'mode': 'create',
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add Fuel Index Pricing',
            'icon': 'fa-gas-pump',
            'js_scripts': [
                static('js/fuel_index_pricing_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self.request.user, 'person')
        form_data = form.cleaned_data

        if form_data['valid_ufn']:
            form.instance.valid_to = None
        else:
            form.instance.valid_to = form_data['valid_to']

        form.instance.update_active_status_based_on_date()

        return super().form_valid(form)


class FuelIndexPricingEditView(AdminPermissionsMixin, BSModalUpdateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndexPricing
    form_class = FuelIndexPricingDetailsForm
    success_message = 'Fuel Index Pricing updated successfully'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'fuel_index': self.object.fuel_index_details.fuel_index,
            'mode': 'edit',
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Fuel Index Pricing',
            'icon': 'fa-gas-pump',
            'js_scripts': [
                static('js/fuel_index_pricing_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self.request.user, 'person')
        form_data = form.cleaned_data

        if form_data['valid_ufn']:
            form.instance.valid_to = None
        else:
            form.instance.valid_to = form_data['valid_to']

        form.instance.update_active_status_based_on_date()

        return super().form_valid(form)


class FuelIndexPricingSupersedeView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndexPricing
    form_class = FuelIndexPricingDetailsForm
    success_message = 'Fuel Index Pricing superseded successfully'
    permission_required = ['pricing.p_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.old_index_pricing = FuelIndexPricing.objects.get(pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        old_index_pricing = FuelIndexPricing.objects.get(pk=self.kwargs['pk'])
        kwargs.update({
            'old_index_pricing': old_index_pricing,
            'fuel_index': old_index_pricing.fuel_index_details.fuel_index,
            'mode': 'supersede'
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Supersede Fuel Index Pricing',
            'icon': 'fa-gas-pump',
            'js_scripts': [
                static('js/fuel_index_pricing_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            form.instance.fuel_index_details = self.old_index_pricing.fuel_index_details
            form.instance.updated_by = getattr(self.request.user, 'person')
            form_data = form.cleaned_data

            if form_data['valid_ufn']:
                form.instance.valid_to = None
            else:
                form.instance.valid_to = form_data['valid_to']

            form.instance.update_active_status_based_on_date()

            # Update end date of old pricing row to end before new one starts
            if self.old_index_pricing.valid_ufn or self.old_index_pricing.valid_to >= form.instance.valid_from:
                self.old_index_pricing.valid_to = form.instance.valid_from - timedelta(days=1)
                self.old_index_pricing.valid_ufn = False
                self.old_index_pricing.update_active_status_based_on_date()

            form.instance.save()
            self.old_index_pricing.superseded_by = form.instance
            self.old_index_pricing.save(update_fields=['is_active', 'valid_to', 'valid_ufn', 'superseded_by'])

        return super().form_valid(form)


class FuelIndexPricingDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndexPricing
    form_class = ConfirmationForm
    success_message = 'Fuel Index has been deleted'
    permission_required = ['pricing.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Fuel Index Pricing',
            'text': f'Are you sure you want to delete this fuel index pricing?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext

        return context


class FuelIndexPricingPublishView(AdminPermissionsMixin, BSModalFormView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = FuelIndexPricing
    form_class = ConfirmationForm
    permission_required = ['pricing.p_publish']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.model.objects.get(pk=self.kwargs['pk'])

        if instance.is_published:
            metacontext = {
                'title': 'Unpublish Fuel Index Pricing',
                'text': f'Are you sure you want to hide this fuel index pricing?',
                'icon': 'fa-minus',
                'action_button_text': 'Unpublish',
                'action_button_class': 'btn-success',
            }
        else:
            metacontext = {
                'title': 'Publish Fuel Index Pricing',
                'text': f'Are you sure you want to publish this fuel index pricing?',
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
            messages.success(self.request, 'Fuel Index has been hidden')
        else:
            instance.is_published = True
            messages.success(self.request, 'Fuel Index has been published')

        instance.save()

        return super().form_valid(form)


# Associated Agreement Pricing Table
class FuelIndexAgreementPricingListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingFormula
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    def render_row_details(self, pk, request=None):
        return render_to_string('fuel_pricing_subtable.html', {
            'object': FuelAgreementPricingFormula.objects.get(id=pk),
            'table_name': 'associated_agreement_pricing',
            'table_url': reverse_lazy('admin:index_pricing_associated_agreement_pricing_sublist_ajax', kwargs={
                'index_pk': self.kwargs['pk'],
                'pk': pk,
            }),
            'js_scripts': [
                static('js/datatables_agreement_pricing_embed.js')
            ]
        })

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_details().filter(
            pricing_index__fuel_index_id=self.kwargs['pk'],
            parent_entry=None
        )

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px'},
        {'name': 'supplier', 'title': 'Supplier', 'visible': True, 'foreign_field': 'agreement__supplier',
         'className': 'url_source_col'},
        {'name': 'icao_iata', 'title': 'Airport/Location', 'visible': True, },
        {'name': 'flight_type', 'title': 'Flight Type(s)', 'visible': True, },
        {'name': 'destination_type', 'title': 'Destination', 'foreign_field': 'destination_type__name',
         'visible': True, },
        {'name': 'operated_as', 'title': 'Operated As', 'visible': True, 'boolean': True,
         'choices': ((0, 'Commercial'), (1, 'Private'), (2, 'Both')), 'defaultContent': '--',
         'sort_field': 'operated_as_status'},
        {'name': 'delivery_methods', 'title': 'Delivery Method', 'm2m_foreign_field': 'delivery_methods__name',
         'visible': True,
         'defaultContent': '--'},
        {'name': 'specific_client', 'title': 'Specific Client', 'visible': True, 'className': 'text-wrap',
         'defaultContent': '--'},
        {'name': 'differential', 'title': 'Differential', 'visible': True, 'width': '140px'},
    ]

    def sort_queryset(self, params, qs):
        orders = [o.column_link.get_field_search_path() for o in params['orders']]

        if 'differential' in orders:
            if 'ASC' in str(params['orders'][0]):
                return  qs.order_by('differential_pricing_unit__description_short', 'differential_value')
            else:
                return  qs.order_by('-differential_pricing_unit__description_short', '-differential_value')
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
                elif column_link.name == 'supplier':
                    search_value = column_link.search_value
                    qs = qs.filter(Q(agreement__supplier__details__registered_name__icontains=search_value) |
                                   Q(agreement__supplier__details__trading_name__icontains=search_value))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs.distinct()

    def customize_row(self, row, obj):
        row['icao_iata'] = f'{obj.icao_iata}'

        related_entries = FuelAgreementPricingFormula.objects.filter(parent_entry=obj.pk)

        if related_entries.exists() or obj.band_uom:
            add_class = 'has_children'
            row['differential'] = f'Quantity Band Applies'
        else:
            add_class = ''
            row['differential'] = obj.get_differential_datatable_str()

        row['supplier'] = f'<span class="{add_class}"' \
                          f'data-url="{obj.agreement.get_absolute_url()}">{obj.agreement.supplier_name}</span>'

        # Note: modified children tables to be universal, we need 'has_children on one of the <td>s

        formatted_flight_type = (obj.flight_type.name).split('Only')[0].strip()
        if formatted_flight_type[-1] != 's': formatted_flight_type += 's'
        row['flight_type'] = formatted_flight_type

        return


# Associated Agreement Pricing Subtable
class FuelIndexAgreementPricingListSubListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = FuelAgreementPricingFormula
    search_values_separator = '+'
    initial_order = [['band_start', "asc"]]
    permission_required = ['pricing.p_view']

    def get_initial_queryset(self, request=None):
        parent_entry = FuelAgreementPricingFormula.objects.with_details().filter(id=self.kwargs['pk'])
        related_entries = FuelAgreementPricingFormula.objects.with_details().filter(parent_entry=self.kwargs['pk'])

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
        {'name': 'dummy_7', 'title': 'Bands', 'placeholder': True, },
    ]

    def customize_row(self, row, obj):

        # Not the best solution, but it gives a better overall look
        for name in row:
            if 'dummy' in name:
                row[name] = ''

        row['band_start'] = f'{obj.band_uom}: {int(obj.band_start)} - {int(obj.band_end)}'
        row['differential'] = obj.get_differential_datatable_str()

        return
