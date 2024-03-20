from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button
from organisation.forms import OrganisationDocumentForm
from organisation.models import OrganisationDocument, Organisation
from user.mixins import AdminPermissionsMixin


class OrganisationDocumentsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationDocument
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = OrganisationDocument.objects.filter(
            organisation_id=self.kwargs['organisation_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False,
            'orderable': False, 'width': '10px'},
        {'name': 'name', 'title': 'Name',  'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'type', 'title': 'Type', 'foreign_field': 'type__name',
            'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'description', 'title': 'Description',  'visible': True, 'searchable': False, },
        {'name': 'actions', 'title': '', 'visible': True,
            'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def customize_row(self, row, obj):
        row['name'] = f'<span data-url="{obj.file.url}">{obj.name}</span>'

        download_btn = get_datatable_actions_button(button_text='',
                                                    button_url=obj.file.url,
                                                    button_class='fa-download text-primary',
                                                    button_active=self.request.user.has_perm('core.p_contacts_view'),
                                                    button_modal=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:organisation_documents_delete', kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = download_btn + delete_btn
        return


class OrganisationDocumentCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationDocument
    form_class = OrganisationDocumentForm
    success_message = 'Document created successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        organisation_id = self.kwargs.get('organisation_id', None)
        organisation = get_object_or_404(Organisation, pk=organisation_id)
        instance = self.model(organisation=organisation)
        kwargs.update({
            'organisation': organisation,
            'instance': instance
        })

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Upload New Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


class OrganisationDocumentDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationDocument
    form_class = ConfirmationForm
    success_message = 'Document has been deleted'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
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
