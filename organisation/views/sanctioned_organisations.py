from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from core.forms import ConfirmationForm
from core.models.ofac_api import OfacApiException
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_organisation_status_badge
from core.utils.ofac_api import OfacApi
from organisation.models import Organisation
from user.mixins import AdminPermissionsMixin


class SanctionedOrganisationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.sanctioned()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True, },
        {'name': 'type', 'title': 'Organisation Type', 'foreign_field': 'details__type__name', 'visible': True},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'className': 'actions', 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        row['actions'] = get_datatable_actions_button(button_text='Ignore',
                                                      button_url=reverse_lazy('admin:sanctioned_organisation_ignore',
                                                                              kwargs={'pk': obj.pk}),
                                                      button_class='btn-outline-primary',
                                                      button_icon='fa-times',
                                                      button_active=self.request.user.has_perm(
                                                          'core.p_contacts_sanctioned_ignore'),
                                                      button_modal=True,
                                                      modal_validation=True)
        return


class SanctionedOrganisationsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Sanctioned Organisations',
            'page_id': 'sanctioned_organisations_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:sanctioned_organisations_ajax',
        }

        context['metacontext'] = metacontext
        return context


class SanctionedOrganisationIgnoreView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = OfacApiException
    form_class = ConfirmationForm
    success_message = 'Exception created successfully'
    permission_required = ['core.p_contacts_sanctioned_ignore']

    organisation = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['pk'])

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create an Exception for Organisation',
            'text': f'Are you sure you want to create an exception for this organisation and ignore the matches in '
                    f'the OFAC database?',
            'icon': 'fa-edit',
            'action_button_text': 'Confirm',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if not self.organisation.ofac_excepted.exists():
                OfacApiException.objects.create(organisation=self.organisation)

            self.organisation.is_sanctioned_ofac = False
            self.organisation.save()

        return super().form_valid(form)


class SanctionsExceptionsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.filter(ofac_excepted__isnull=False)

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True, },
        {'name': 'type', 'title': 'Organisation Type', 'foreign_field': 'details__type__name', 'visible': True, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False,
         'className': 'organisation_status'},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'className': 'actions', 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        row['actions'] = get_datatable_actions_button(button_text='Delete',
                                                      button_url=reverse_lazy('admin:sanctions_exception_delete',
                                                                              kwargs={'pk': obj.pk}),
                                                      button_class='btn-outline-primary',
                                                      button_icon='fa-times',
                                                      button_active=self.request.user.has_perm(
                                                          'core.p_contacts_sanctioned_delete'),
                                                      button_modal=True,
                                                      modal_validation=True)
        return


class SanctionsExceptionsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Sanctioned Organisations - Exception List',
            'page_id': 'sanctioned_organisations_exceptions_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:sanctions_exceptions_ajax',
        }

        context['metacontext'] = metacontext
        return context


class SanctionExceptionDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = OfacApiException
    form_class = ConfirmationForm
    success_message = 'Exception deleted successfully'
    permission_required = ['core.p_contacts_sanctioned_delete']

    organisation = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['pk'])

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete an Exception for Organisation',
            'text': f'Are you sure you want to delete the exception for this organisation? '
                    f'The OFAC database will be re-checked for sanctions on this organisation upon confirmation.',
            'icon': 'fa-edit',
            'action_button_text': 'Delete',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if self.organisation.ofac_excepted.exists():
                self.organisation.ofac_excepted.all().delete()

                # Re-check the organisations ofac status
                status_trading_name = None
                ofac = OfacApi(api_key=settings.OFAC_API_KEY, min_score=95)

                status_registered_name = ofac.search_by_name(
                    self.organisation.details.registered_name, 'Entity')

                if self.organisation.details.trading_name:
                    status_trading_name = ofac.search_by_name(
                        self.organisation.details.trading_name, 'Entity')

                ofac_status = any([status_registered_name, status_trading_name])
                self.organisation.is_sanctioned_ofac = ofac_status
                self.organisation.ofac_latest_update = timezone.now()
                self.organisation.save()

        return super().form_valid(form)
