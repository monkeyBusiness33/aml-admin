from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalUpdateView
from bootstrap_modal_forms.mixins import is_ajax

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_badge
from organisation.forms import PaymentMethodForm
from organisation.models import OrganisationAcceptedPaymentMethod, OrganisationPaymentMethod
from user.mixins import AdminPermissionsMixin


class AcceptedPaymentMethodAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationAcceptedPaymentMethod
    search_values_separator = '+'
    initial_order = []
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['organisation.view_organisationacceptedpaymentmethod']
    context_object_name = 'payment_methods'

    def get_initial_queryset(self, request=None):
        return self.model.objects.with_details().filter(organisation=self.kwargs['pk'])

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'payment_method', 'title': 'Name', 'foreign_field': 'payment_method__name' },
        {'name': 'currency', 'title': 'Currency', 'sort_field': 'currency__name', 'width': '300px', },
        {'name': 'methods_str', 'title': 'Methods', 'orderable': False, 'width': '300px', },
        {'name': 'actions', 'title': '', 'placeholder': True, 'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['methods_str'] = ''.join([get_datatable_badge(
                badge_text=method,
                badge_class='bg-gray-600 datatable-badge-normal badge-multiline badge-250',
                tooltip_enable_html=True
            ) for method in obj.payment_method.methods_list.split(', ')])

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:organisation_payment_methods_edit',
                                                    kwargs={'entity_pk': self.kwargs['pk'], 'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=True,
                                                button_modal=True,
                                                modal_validation=True)
        del_btn = get_datatable_actions_button(button_text='',
                                               button_url=reverse_lazy(
                                                   'admin:organisation_payment_methods_delete',
                                                   kwargs={'entity_pk': self.kwargs['pk'], 'pk': obj.pk}),
                                               button_class='fa-trash text-danger',
                                               button_active=True,
                                               button_modal=True,
                                               modal_validation=False)

        row['actions'] = edit_btn + del_btn


class PaymentMethodCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationPaymentMethod
    form_class = PaymentMethodForm
    success_message = 'Payment Method added successfully'
    permission_required = ['organisation.add_organisationacceptedpaymentmethod']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        entity_pk = self.kwargs.get('entity_pk')
        kwargs.update({'organisation': entity_pk})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Add New Payment Method',
            'icon': 'fa-plus',
        }

        context['metacontext'] = metacontext
        return context

class PaymentMethodEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationPaymentMethod
    form_class = PaymentMethodForm
    success_message = 'Payment Method edited successfully'
    permission_required = ['organisation.change_organisationacceptedpaymentmethod']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        entity_pk = self.kwargs.get('entity_pk')
        kwargs.update({'organisation': entity_pk})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Edit Payment Method',
            'icon': 'fa-edit',
        }

        context['metacontext'] = metacontext
        return context


class AcceptedPaymentMethodDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationAcceptedPaymentMethod
    form_class = ConfirmationForm
    success_message = 'Payment method deleted successfully'
    permission_required = ['organisation.delete_organisationacceptedpaymentmethod']

    def get_success_url(self):
        return reverse_lazy('admin:ground_handler', kwargs={'pk': self.kwargs['entity_pk']})

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        metacontext = {
            'title': 'Delete Comment',
            'text': f'Are you sure you want to delete this payment method?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            payment_method = OrganisationPaymentMethod.objects.get(id = self.object.payment_method.id)
            payment_method.delete()

        return super().form_valid(form)
