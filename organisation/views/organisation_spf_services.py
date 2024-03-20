from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button
from organisation.forms import HandlerSpfServiceFormSet
from organisation.models import HandlerSpfService, Organisation
from user.mixins import AdminPermissionsMixin


class OrganisationHandlerSpfServicesAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = HandlerSpfService
    search_values_separator = '+'
    permission_required = ['handling.p_dla_services_view']

    organisation = None

    def get_initial_queryset(self, request=None):
        return self.model.objects.filter(handler_id=self.kwargs['organisation_id'])

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'service', 'title': 'Service Name', 'foreign_field': 'dla_service__name', 'visible': True},
        {'name': 'applies_after_minutes', 'visible': True, },
        {'name': 'applies_if_pax_onboard', 'visible': True, },
        {'name': 'applies_if_cargo_onboard', 'visible': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'actions'},
    ]

    def customize_row(self, row, obj):
        if obj.applies_if_pax_onboard:
            row['applies_if_pax_onboard'] = get_fontawesome_icon(icon_name='check-circle text-success',
                                                                 tooltip_text="Applies")
        else:
            row['applies_if_pax_onboard'] = get_fontawesome_icon(icon_name='ban text-danger',
                                                                 tooltip_text="Not Applies")

        if obj.applies_if_cargo_onboard:
            row['applies_if_cargo_onboard'] = get_fontawesome_icon(icon_name='check-circle text-success',
                                                                   tooltip_text="Applies")
        else:
            row['applies_if_cargo_onboard'] = get_fontawesome_icon(icon_name='ban text-danger',
                                                                   tooltip_text="Not Applies")

        detach_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:organisation_spf_services_mapping_delete',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'handling.p_dla_services_update'),
                                                  button_modal=True,
                                                  modal_validation=False)
        row['actions'] = detach_btn
        return


class OrganisationHandlerSpfServicesDetachView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = HandlerSpfService
    form_class = ConfirmationForm
    success_message = 'SPF Service deleted successfully'
    permission_required = ['handling.p_dla_services_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()

        metacontext = {
            'icon': 'fa-trash',
            'title': 'Delete SPF Service Mapping',
            'text': f'Please confirm deletion of the mapping service <b>"{service.dla_service.name}"</b> from Handler',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Confirm',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            spf_service = self.get_object()
            spf_service.handler.activity_log.create(
                author=getattr(self, 'person'),
                record_slug='organisation_spf_service_to_auto_select_deleted',
                details=f'Removed SPF Service to Auto-Select: "{spf_service.dla_service.name}"'
            )
        return super().form_valid(form)


class HandlerManageSpfServices(AdminPermissionsMixin, BSModalFormView):
    template_name = 'organisations_pages_includes/_modal_handler_manage_spf_services.html'
    model = HandlerSpfService
    form_class = HandlerSpfServiceFormSet
    permission_required = ['handling.p_dla_services_update']

    handler = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handler = get_object_or_404(Organisation, pk=self.kwargs['organisation_id'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handler': self.handler})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Add Services',
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Add',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, formset):
        if not is_ajax(self.request.META):
            formset.save()
            for form in formset:
                if form.instance.pk:
                    self.handler.activity_log.create(
                        author=getattr(self, 'person'),
                        record_slug='organisation_spf_service_to_auto_select_added',
                        details=f'Added SPF Service to Auto-Select: "{form.instance.dla_service.name}"'
                    )
        return super().form_valid(formset)
