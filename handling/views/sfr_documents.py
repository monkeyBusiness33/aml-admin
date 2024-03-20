from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalReadView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button
from handling.forms.sfr_documents import HandlingRequestDocumentForm
from handling.models import HandlingRequestDocument, HandlingRequest
from user.mixins import AdminPermissionsMixin


class HandlingRequestDocumentsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = HandlingRequestDocument
    search_values_separator = '+'
    permission_required = ['handling.p_view']
    initial_order = [["created_at", "desc"], ]

    def get_initial_queryset(self, request=None):
        qs = HandlingRequestDocument.objects.filter(
            handling_request_id=self.kwargs['pk'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, },
        {'name': 'type', 'title': 'Type', 'foreign_field': 'type__name', 'visible': True, 'width': '30px', },
        {'name': 'description', 'title': 'Description', 'visible': True, },
        {'name': 'is_dod_viewable', 'title': 'Viewable by Client?', 'choices': True, },
        {'name': 'created_by', 'title': 'Created By', 'visible': True, 'orderable': True, 'searchable': False,
         'width': '40px', },
        {'name': 'created_at', 'title': 'Created At', 'visible': True, 'orderable': True, 'searchable': False,
         'width': '40px', },
        {'name': 'is_signed', 'title': 'Signed?', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '100px', 'className': 'sfr_documents_is_signed', },
        {'name': 'signed_by', 'title': 'Signed By', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'width': '100px', },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False,
         'className': 'actions', 'width': '100px', },
    ]

    def customize_row(self, row, obj):
        row['created_by'] = obj.created_by.fullname if obj.created_by else ''
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")

        if obj.is_dod_viewable:
            row['is_dod_viewable'] = get_datatable_actions_button(button_text='',
                                                                  button_url=reverse_lazy(
                                                                      'admin:handling_document_show_hide',
                                                                      kwargs={'pk': obj.pk}),
                                                                  button_class='fa-eye text-success',
                                                                  button_popup="Viewable",
                                                                  button_active=self.request.user.has_perm(
                                                                      'handling.p_update'),
                                                                  button_modal=True,
                                                                  modal_validation=True)
        else:
            row['is_dod_viewable'] = get_datatable_actions_button(button_text='',
                                                                  button_url=reverse_lazy(
                                                                      'admin:handling_document_show_hide',
                                                                      kwargs={'pk': obj.pk}),
                                                                  button_class='fa-eye-slash text-danger',
                                                                  button_popup="Hidden",
                                                                  button_active=self.request.user.has_perm(
                                                                      'handling.p_update'),
                                                                  button_modal=True,
                                                                  modal_validation=True)

        is_signed_html = ''
        if not obj.recent_file or obj.recent_file.is_signed is None:
            is_signed_html = 'N/A'
        elif obj.recent_file.is_signed is False:
            is_signed_html = get_fontawesome_icon(icon_name='times', tooltip_text='Not Signed',
                                                  hidden_value='not_signed')
        elif obj.recent_file.is_signed is True:
            is_signed_html = get_fontawesome_icon(icon_name='check', tooltip_text='Signed', hidden_value='signed')

        row['is_signed'] = is_signed_html

        signed_by_html = '--'
        if obj.recent_file and obj.recent_file.signed_by:
            signed_by_html = obj.recent_file.signed_by.fullname

        row['signed_by'] = signed_by_html

        download_btn = get_datatable_actions_button(button_text='',
                                                    button_popup='Download File',
                                                    button_url=obj.recent_file_download_url,
                                                    button_class='fa-file-download',
                                                    button_active=self.request.user.has_perm('handling.p_view'),
                                                    button_modal=False)

        history_btn = ''
        if obj.files.filter(is_recent=False).exists():
            history_btn = get_datatable_actions_button(button_text='',
                                                       button_popup='Document History',
                                                       button_url=reverse_lazy(
                                                           'admin:handling_request_document_history',
                                                           kwargs={'pk': obj.pk}),
                                                       button_class='fa-history',
                                                       button_active=self.request.user.has_perm('handling.p_view'),
                                                       button_modal=True,
                                                       modal_validation=False)

        update_btn = get_datatable_actions_button(button_text='',
                                                  button_popup='Update Document',
                                                  button_url=reverse_lazy(
                                                      'admin:handling_request_document_update',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-edit',
                                                  button_active=self.request.user.has_perm('handling.p_update'),
                                                  button_modal=True,
                                                  modal_validation=True)

        row['actions'] = download_btn + update_btn + history_btn
        return


class HandlingRequestDocumentCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = HandlingRequestDocumentForm
    success_message = 'Document successfully created'
    permission_required = ['handling.p_create']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['handling_request_id'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        request_person = getattr(self.request.user, 'person')

        instance = self.model(
            handling_request=self.handling_request,
            created_by=request_person,
            is_staff_added=self.request.user.is_staff,
        )
        kwargs.update({'instance': instance})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create S&F Request Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestDocumentUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = HandlingRequestDocumentForm
    success_message = 'Document successfully updated'
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Update S&F Request Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


class HandlingRequestDocumentHistoryView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'handling_request/43_document_history_modal.html'
    model = HandlingRequestDocument
    permission_required = ['handling.p_view']
    context_object_name = 'document'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'History of S&F Request Document',
            'icon': 'fa-history',
        }

        context['metacontext'] = metacontext
        return context


class HandlingDocumentDoDShowHideView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['handling.p_update']

    document = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.document = get_object_or_404(HandlingRequestDocument, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.document.is_dod_viewable:
            metacontext = {
                'title': 'Make Viewable by Client',
                'icon': 'fa-eye',
                'text': f'Please confirm you want to open viewing <b>{self.document}</b> for clients.',
                'action_button_text': 'Open Viewing',
                'action_button_class': 'btn-success',
            }
        else:
            metacontext = {
                'title': 'Disable Viewing by Client',
                'icon': 'fa-eye-slash',
                'text': f'Please confirm you want to disable viewing <b>{self.document}</b> by clients.',
                'action_button_text': 'Disable Viewing',
                'action_button_class': 'btn-danger',
            }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            self.document.is_dod_viewable = not self.document.is_dod_viewable
            self.document.save()

            if self.document.is_dod_viewable:
                messages.success(self.request, f'Document made viewable for clients')
            else:
                messages.warning(self.request, f'Document hidden for clients')

        return super().form_valid(form)
