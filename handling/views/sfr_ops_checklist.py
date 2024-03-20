import json
from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_fontawesome_icon
from handling.forms.sfr_ops_checklist import SfrOpsChecklistItemForm
from handling.models import HandlingRequest, HandlingRequestOpsChecklistItem, SfrOpsChecklistParameter
from user.mixins import AdminPermissionsMixin


class SfrOpsChecklistSettingsView(AdminPermissionsMixin, TemplateView):
    template_name = 'handling_sfr_ops_checklist_settings/00_sfr_ops_checklist_settings.html'
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'template_items': SfrOpsChecklistParameter.objects.filter(location__isnull=True, is_active=True),
            'location_specific_items': SfrOpsChecklistParameter.objects.filter(location__isnull=False, is_active=True),
        })

        metacontext = {
            'title': 'Ops Checklist Settings',
        }

        context['metacontext'] = metacontext
        return context


class SfrOpsChecklistSettingsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SfrOpsChecklistParameter
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["category", "asc"], ["description", "asc"], ["url", "asc"], ]
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'category', 'title': 'Category', 'foreign_field': 'category__name'},
        {'name': 'description', 'title': 'Description', 'defaultContent': '--', },
        {'name': 'url', 'title': 'URL', 'defaultContent': '--',
         'className': 'url_source_col single_cell_link text-primary'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '120px', 'className': 'actions', },
    ]

    def get_initial_queryset(self, request=None):
        return self.model.objects.filter(is_active=True, location__isnull=True)

    def customize_row(self, row, obj):
        if row['url']:
            row['url'] = f"<span data-url='{row['url']}' data-target='_blank'>{row['url']}</span>"

        edit_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:sfr_ops_checklist_settings_update_item', kwargs={'pk': obj.pk}),
            button_class='fa-edit text-primary',
            button_active=self.request.user.has_perm('handling.p_manage_sfr_ops_checklist_settings'),
            button_modal=True,
            modal_validation=True)
        del_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:sfr_ops_checklist_settings_delete_item', kwargs={'pk': obj.pk}),
            button_class='ml-2 text-danger fa-trash',
            button_active=self.request.user.has_perm('handling.p_manage_sfr_ops_checklist_settings'),
            button_modal=True,
            modal_validation=False
        )
        row['actions'] = edit_btn + del_btn


class SfrOpsChecklistSettingsLocationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = SfrOpsChecklistParameter
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["location_str", "asc"], ["category", "asc"], ["description", "asc"], ["url", "asc"], ]
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'location_str', 'title': 'Location', },
        {'name': 'category', 'title': 'Category', 'foreign_field': 'category__name'},
        {'name': 'description', 'title': 'Description', 'defaultContent': '--', },
        {'name': 'url', 'title': 'URL', 'defaultContent': '--',
         'className': 'url_source_col single_cell_link text-primary'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '120px', 'className': 'actions', },
    ]

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_details().filter(is_active=True, location__isnull=False)

    def customize_row(self, row, obj):
        if row['url']:
            row['url'] = f"<span data-url='{row['url']} data-target='_blank'>{row['url']}</span>"

        edit_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:sfr_ops_checklist_settings_update_item', kwargs={'pk': obj.pk}) + '?location-specific=1',
            button_class='fa-edit text-primary',
            button_active=self.request.user.has_perm('handling.p_manage_sfr_ops_checklist_settings'),
            button_modal=True,
            modal_validation=True)
        del_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy(
                'admin:sfr_ops_checklist_settings_delete_item', kwargs={'pk': obj.pk}),
            button_class='ml-2 text-danger fa-trash',
            button_active=self.request.user.has_perm('handling.p_manage_sfr_ops_checklist_settings'),
            button_modal=True,
            modal_validation=False
        )
        row['actions'] = edit_btn + del_btn


class SfrOpsChecklistSettingsItemCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = SfrOpsChecklistParameter
    form_class = SfrOpsChecklistItemForm
    success_message = 'Checklist Template Item created successfully'
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'location_specific': bool(self.request.GET.get('location-specific', False))
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add Checklist Template Item',
            'icon': 'fa-plus',
            'js_scripts': [
                static('js/sfr_ops_checklist_item_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context


class SfrOpsChecklistSettingsItemEditView(AdminPermissionsMixin, BSModalUpdateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = SfrOpsChecklistParameter
    form_class = SfrOpsChecklistItemForm
    success_message = 'Checklist Template Item updated successfully'
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'location_specific': bool(self.request.GET.get('location-specific', False))
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Checklist Template Item',
            'icon': 'fa-edit',
            'js_scripts': [
                static('js/sfr_ops_checklist_item_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context


class SfrOpsChecklistSettingsItemDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = SfrOpsChecklistParameter
    form_class = ConfirmationForm
    success_message = 'Checklist Template Item has been deleted'
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Checklist Template Item',
            'text': f'Are you sure you want to delete this Checklist Template Item?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.is_active=False
        self.object.save()

        return HttpResponseRedirect(success_url)


class HandlingRequestOpsChecklistItemCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = SfrOpsChecklistParameter
    form_class = SfrOpsChecklistItemForm
    success_message = 'Checklist Item created successfully'
    permission_required = ['handling.p_manage_sfr_ops_checklist_settings']

    handling_request = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=kwargs.get('request_pk'))

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'location_specific': True,
            'fixed_location': self.handling_request.airport,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add Checklist Item',
            'icon': 'fa-plus',
            'js_scripts': [
                static('js/sfr_ops_checklist_item_modal.js')
            ],
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        # This view should also create an instance of the newly created
        # template item for the handling request from which it was added.
        response = super().form_valid(form)

        if not is_ajax(self.request.META) and form.instance.pk is not None:
            HandlingRequestOpsChecklistItem.objects.create(
                request=self.handling_request,
                checklist_item=form.instance
            )

        return response


class HandlingRequestOpsChecklistAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = HandlingRequestOpsChecklistItem
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["is_completed", "asc"], ["category", "asc"], ["description", "asc"], ["url", "asc"], ]
    permission_required = ['handling.p_view']

    handling_request = None

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'is_completed', 'title': 'Done', 'width': '50px', 'searchable': False,
         'className': 'is_completed' },
        {'name': 'category', 'title': 'Category', 'width': '200px',
         'foreign_field': 'checklist_item__category__name', },
        {'name': 'description', 'title': 'Description', 'foreign_field': 'checklist_item__description',
         'defaultContent': '--', },
        {'name': 'url', 'title': 'URL', 'foreign_field': 'checklist_item__url',
         'defaultContent': '--', 'className': 'url_source_col single_cell_link text-primary'},
    ]

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=kwargs.get('request_pk'))


    def get_initial_queryset(self, request=None):
        return self.model.objects.filter(request=self.handling_request)

    def customize_row(self, row, obj):
        if row['url']:
            row['url'] = f"<span data-url='{row['url']}' data-target='_blank'>{row['url']}</span>"

        toggle_completed_url = reverse_lazy('admin:handling_request_ops_checklist_complete_item',
                                            kwargs={'request_pk': self.handling_request.pk, 'pk': obj.pk})
        completed_classes = ' completed-item text-success' if obj.is_completed else ''
        complete_btn = get_fontawesome_icon(
            icon_name='check',
            additional_classes=f'fa-check text-primary interactive-icon{completed_classes}',
            tooltip_text='Mark as done' if not obj.is_completed else 'Mark as outstanding'
        )
        row['is_completed'] = (f"<span class='d-block w-100 text-center toggle-item-completed-btn' "
                               f"data-ajax-url='{toggle_completed_url}'>{complete_btn}</span>")


class HandlingRequestOpsChecklistItemCompleteView(AdminPermissionsMixin, View):
    permission_required = ['handling.p_view']

    handling_request = None
    checklist_item = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=kwargs.get('request_pk'))
        self.checklist_item = get_object_or_404(HandlingRequestOpsChecklistItem, pk=kwargs.get('pk'))
        self.url = reverse_lazy('admin:handling_request', kwargs={'pk': kwargs.get('request_pk')})

    def post(self, request, *args, **kwargs):
        # Toggle the item's completed status
        item = self.checklist_item
        item_data = {
            'category': item.checklist_item.category.name,
            'description': item.checklist_item.description,
            'url': item.checklist_item.url
        }

        if not item.is_completed:
            item.is_completed = True
            item.completed_by = self.request.user.person
            item.completed_at = datetime.now()

            item.request.activity_log.create(
                value_prev=0, value_new=1,
                record_slug='sfr_ops_checklist_item_status_change',
                author=self.request.user.person,
                data=item_data
            )
        else:
            item.is_completed = False
            item.completed_by = None
            item.completed_at = None

            item.request.activity_log.create(
                value_prev=1, value_new=0,
                record_slug='sfr_ops_checklist_item_status_change',
                author=self.request.user.person,
                data=item_data
            )

        item.save()

        return HttpResponse(json.dumps({
            'is_completed': item.is_completed,
            'status_badge_html': item.request.ops_checklist_status_badge,
        }), status=200)
