import json

from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView

from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button, get_datatable_badge
from handling.forms.dla_services import DlaServiceForm
from organisation.models import DlaService
from user.mixins import AdminPermissionsMixin


class DlaServicesListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = DlaService
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['handling.p_dla_services_view']

    def get_initial_queryset(self, request=None):
        return self.model.objects.active()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Service Name', 'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'is_spf_included', 'title': 'Included in SPF?', 'visible': True, 'width': '10px'},
        {'name': 'charge_services', 'title': 'Mapped Services', 'm2m_foreign_field': 'charge_services__name',
         'visible': True},
        {'name': 'actions', 'title': 'Actions', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'width': '20px'},
    ]

    def customize_row(self, row, obj):
        if obj.is_spf_included:
            row['is_spf_included'] = get_fontawesome_icon(icon_name='check-circle text-success', tooltip_text="Yes")
        else:
            row['is_spf_included'] = get_fontawesome_icon(icon_name='ban text-danger', tooltip_text="No")

        row['charge_services'] = ''.join([get_datatable_badge(
            badge_text=charge_service.name,
            badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
        ) for charge_service in obj.charge_services.all()])

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:handling_dla_services_edit', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit text-primary',
                                                button_active=self.request.user.has_perm(
                                                    'handling.p_dla_services_update'),
                                                button_modal=True,
                                                modal_validation=True)
        row['actions'] = edit_btn
        del_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                    'admin:handling_dla_services_delete', kwargs={'pk': obj.pk}),
                                               button_class='ml-2 text-danger fa-trash-alt',
                                               button_active=self.request.user.has_perm(
                                                   'handling.p_dla_services_update'),
                                               button_modal=True,
                                               modal_validation=False)
        row['actions'] += del_btn


class DlaServicesListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['handling.p_dla_services_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add DLA Service',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:handling_dla_services_create'),
             'button_modal': True,
             'button_perm': self.request.user.has_perm('handling.p_dla_services_update')},
        ]

        metacontext = {
            'title': 'DLA Services Settings',
            'page_id': 'dla_services_list',
            'datatable_uri': 'admin:handling_dla_services_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class DlaServiceCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = DlaService
    form_class = DlaServiceForm
    permission_required = ['handling.p_dla_services_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add DLA Service',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context


class DlaServiceEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = DlaService
    form_class = DlaServiceForm
    success_message = 'Service details has been updated'
    permission_required = ['handling.p_dla_services_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit DLA Service',
            'icon': 'fa-edit',
        }

        context['metacontext'] = metacontext
        return context


class DlaServiceDeleteView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = DlaService
    form_class = ConfirmationForm
    success_message = 'Service details has been delete'
    permission_required = ['handling.p_dla_services_update']

    dla_service = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.dla_service = get_object_or_404(DlaService, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete DLA Service',
            'icon': 'fa-trash',
            'text': "Please confirm DLA service deletion",
            'action_button_text': "Delete",
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            self.dla_service.is_deleted = True
            self.dla_service.save()
        return super().form_valid(form)
