from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalDeleteView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from administration.forms.email_distribution_control import EmailDistributionControlAddressForm, \
    EmailDistributionControlRuleForm
from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_actions_button, get_fontawesome_icon
from organisation.models import OrganisationEmailControlAddress, OrganisationEmailControlRule
from user.mixins import AdminPermissionsMixin


class EmailDistributionControlView(AdminPermissionsMixin, TemplateView):
    template_name = 'email_distribution_control.html'
    permission_required = ['administration.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Email Distribution Control',
            'page_id': 'email_distribution_control',
        }

        context['metacontext'] = metacontext
        return context


class EmailDistributionControlAddressesAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = OrganisationEmailControlAddress
    permission_required = ['administration.p_view']
    search_values_separator = '+'
    length_menu = [[10, 50, 100, 250, -1], [10, 50, 100, 250, 'all']]

    disable_queryset_optimization_only = True
    prefetch_related = {
        'organisation_person__person__details',
        'organisation__airport_details',
        'email_control_rules',
    }

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'searchable': False, 'orderable': True, 'width': 30, },
        {'name': 'label', 'visible': True, },
        {'name': 'organisation_person', 'title': 'Person',
         'foreign_field': 'organisation_person__person__details__first_name', 'visible': True, },
        {'name': 'organisation', 'title': 'Organisation',
         'foreign_field': 'organisation__details__registered_name', 'visible': True, },
        {'name': 'email_address', 'visible': True, },
        {'name': 'applicable_rules', 'title': 'Applicable Rules', 'placeholder': True,
         'searchable': False, 'orderable': False, },
        {'name': 'actions', 'title': 'Actions', 'placeholder': True, 'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['label'] = obj.label or '--'
        row['organisation_person'] = obj.organisation_person.person.fullname if obj.organisation_person else '--'
        row['organisation'] = obj.organisation.full_repr if obj.organisation else '--'
        row['email_address'] = ', '.join(obj.get_email_address())
        row['applicable_rules'] = obj.email_control_rules.count()

        row['actions'] = ''
        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:email_distribution_control_addresses_edit',
                                                    kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'administration.p_email_distribution_control'),
                                                button_modal=True,
                                                modal_validation=True)
        row['actions'] += edit_btn

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:email_distribution_control_addresses_delete',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'administration.p_email_distribution_control'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] += delete_btn


class EmailDistributionControlAddressCreateUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationEmailControlAddress
    form_class = EmailDistributionControlAddressForm
    permission_required = ['administration.p_email_distribution_control']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        address = self.get_object()
        metacontext = {
            'icon': 'fa-at',
        }

        if address:
            metacontext['title'] = 'Edit Email Address'
            metacontext['action_button_text'] = 'Update'
        else:
            metacontext['title'] = 'Add Email Address'
            metacontext['action_button_text'] = 'Create'

        context['metacontext'] = metacontext
        return context


class EmailDistributionControlAddressDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationEmailControlAddress
    form_class = ConfirmationForm
    success_message = 'Address deleted successfully'
    permission_required = ['administration.p_email_distribution_control']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        address = self.get_object()

        metacontext = {
            'icon': 'fa-trash',
            'title': 'Delete Email Address',
            'text': f'Please confirm deletion of email address',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        if address.email_control_rules.exists():
            metacontext['alerts'] = [
                {
                    'text': "This email address is used in multiple rules and can't be deleted.",
                    'class': 'alert-danger',
                    'icon': 'ban',
                    'position': 'top',
                }
            ]
            metacontext['text'] = None
            metacontext['hide_action_button'] = True

        context['metacontext'] = metacontext
        return context


class EmailDistributionControlSpecificRecipientRulesAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = OrganisationEmailControlRule
    permission_required = ['administration.p_view']
    search_values_separator = '+'
    length_menu = [[10, 50, 100, 250, -1], [10, 50, 100, 250, 'all']]
    initial_order = [["created_at", "desc"], ]

    def get_initial_queryset(self, request=None):
        rule_target = self.kwargs.get('rule_target')
        return self.model.objects.filter(
            Q(**{f'{rule_target}__isnull': False})
        )

    disable_queryset_optimization_only = True
    prefetch_related = {
        'recipient_organisation__details',
        'recipient_organisation__airport_details',
    }

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'searchable': False, 'orderable': True, 'width': 30, },

        # Optional columns (displaying adjusted in get_column_defs() method)
        {'name': 'recipient_organisation', 'title': 'Organisation Name',
         'foreign_field': 'recipient_organisation__details__registered_name', 'visible': True},
        {'name': 'recipient_based_airport', 'title': 'Recipient Based Airport',
         'foreign_field': 'recipient_based_airport__airport_details__icao_code', 'visible': True},
        {'name': 'recipient_based_country', 'title': 'Recipient Based Country',
         'foreign_field': 'recipient_based_country__name', 'visible': True},

        {'name': 'email_function', 'title': 'Email Function', 'foreign_field': 'email_function__name'},
        {'name': 'aml_email', 'title': 'Address to Cc/Bcc', 'foreign_field': 'aml_email__organisation__addresses'},
        {'name': 'is_cc', 'visible': True, 'choices': True, 'autofilter': True},
        {'name': 'is_bcc', 'visible': True, 'choices': True, 'autofilter': True},
        {'name': 'created_by', 'title': 'Created By', 'foreign_field': 'created_by__details__first_name'},
        {'name': 'created_at', 'visible': True, 'searchable': False},
        {'name': 'actions', 'title': 'Actions', 'placeholder': True, 'searchable': False, 'orderable': False, },
    ]

    def get_column_defs(self, request):
        # Hide optional columns based on page type (rule_target)
        rule_target = self.kwargs.get('rule_target')
        dynamic_fields = ['recipient_organisation', 'recipient_based_airport', 'recipient_based_country']
        dynamic_fields.remove(rule_target)

        for column in self.column_defs:
            if column['name'] in dynamic_fields:
                column['visible'] = False
            if column['name'] == rule_target:
                column['visible'] = True

        return self.column_defs

    def customize_row(self, row, obj):
        if obj.recipient_organisation:
            row['recipient_organisation'] = '<span data-target="_blank" data-url="{url}">{name}</span>'.format(
                url=obj.recipient_organisation.get_absolute_url(),
                name=obj.recipient_organisation.full_repr,
            )
        if obj.recipient_based_airport:
            row['recipient_based_airport'] = obj.recipient_based_airport.short_repr

        row['aml_email'] = ', '.join(obj.aml_email.get_email_address())

        if obj.is_cc:
            row['is_cc'] = get_fontawesome_icon(icon_name='check-circle text-success', tooltip_text="Yes")
        else:
            row['is_cc'] = get_fontawesome_icon(icon_name='ban text-danger', tooltip_text="No")

        if obj.is_bcc:
            row['is_bcc'] = get_fontawesome_icon(icon_name='check-circle text-success', tooltip_text="Yes")
        else:
            row['is_bcc'] = get_fontawesome_icon(icon_name='ban text-danger', tooltip_text="No")

        row['created_by'] = obj.created_by.fullname
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")

        row['actions'] = ''
        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:email_distribution_control_rule_edit',
                                                    kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'administration.p_email_distribution_control'),
                                                button_modal=True,
                                                modal_validation=True)
        row['actions'] += edit_btn

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:email_distribution_control_rule_delete',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'administration.p_email_distribution_control'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] += delete_btn


class EmailDistributionControlRuleCreateUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationEmailControlRule
    form_class = EmailDistributionControlRuleForm
    permission_required = ['administration.p_email_distribution_control']

    rule_target = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.rule_target = self.kwargs.get('rule_target')

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'rule_target': self.rule_target})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        address = self.get_object()
        metacontext = {
            'icon': 'fa-at',
        }

        if address:
            metacontext['title'] = 'Edit Email Rule'
            metacontext['action_button_text'] = 'Update'
        else:
            metacontext['title'] = 'Add New Rule'
            metacontext['action_button_text'] = 'Create'

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if not form.instance.pk:
                form.instance.created_by = getattr(self, 'person')
                messages.success(self.request, f'Rule successfully added')
        return super().form_valid(form)


class EmailDistributionControlRuleDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationEmailControlRule
    form_class = ConfirmationForm
    success_message = 'Rule deleted successfully'
    permission_required = ['administration.p_email_distribution_control']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'icon': 'fa-trash',
            'title': 'Delete Email Rule',
            'text': f'Please confirm deletion of email CC/BCC rule',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }
        context['metacontext'] = metacontext
        return context
