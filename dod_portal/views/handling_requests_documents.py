from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalReadView
from django.db.models import Q
from django.http import Http404
from django.urls import reverse_lazy

from core.utils.datatables_functions import get_datatable_actions_button, get_fontawesome_icon
from dod_portal.mixins import DodPermissionsMixin
from handling.forms.sfr_documents import HandlingRequestDocumentForm
from handling.models import HandlingRequestDocument


class HandlingRequestDocumentsListAjaxView(DodPermissionsMixin, AjaxDatatableView):
    model = HandlingRequestDocument
    search_values_separator = '+'
    initial_order = [["created_at", "desc"], ]

    def get_initial_queryset(self, request=None):
        position = request.dod_selected_position
        missions = position.get_sfr_list()
        handling_request = missions.filter(pk=self.kwargs['handling_request_id']).first()

        qs = HandlingRequestDocument.objects.filter(
            is_dod_viewable=True,
            handling_request=handling_request,
        )
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, },
        {'name': 'type', 'title': 'Type', 'foreign_field': 'type__name', 'visible': True, 'width': '30px', },
        {'name': 'description', 'title': 'Description', 'visible': True, },
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
                                                    button_active=True,
                                                    button_modal=False)

        update_btn = get_datatable_actions_button(button_text='',
                                                  button_popup='Update Document',
                                                  button_url=reverse_lazy(
                                                      'dod:request_document_update',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-edit',
                                                  button_active=not obj.is_staff_added,
                                                  button_modal=True,
                                                  modal_validation=True)

        history_btn = ''
        if obj.files.filter(is_recent=False).exists():
            history_btn = get_datatable_actions_button(button_text='',
                                                       button_popup='Document History',
                                                       button_url=reverse_lazy(
                                                           'dod:request_document_history',
                                                           kwargs={'pk': obj.pk}),
                                                       button_class='fa-history',
                                                       button_active=True,
                                                       button_modal=True,
                                                       modal_validation=False)

        row['actions'] = download_btn + update_btn + history_btn
        return


class HandlingRequestDocumentCreateView(DodPermissionsMixin, BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = HandlingRequestDocumentForm
    success_message = 'Document successfully created'

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        position = request.dod_selected_position
        missions = position.get_sfr_list()
        self.handling_request = missions.filter(pk=self.kwargs['handling_request_id']).first()
        if not self.handling_request:
            raise Http404(
                "No documents matches the given query."
            )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        request_person = getattr(self.request.user, 'person')

        instance = self.model(
            handling_request=self.handling_request,
            created_by=request_person,
            is_staff_added=False,
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


class HandlingRequestDocumentUpdateView(DodPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = HandlingRequestDocumentForm
    success_message = 'Document successfully updated'

    def has_permission(self):
        document = self.get_object()
        if document.is_staff_added:
            return False
        return True

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


class HandlingRequestDocumentHistoryView(DodPermissionsMixin, BSModalReadView):
    template_name = 'handling_request/43_document_history_modal.html'
    model = HandlingRequestDocument
    context_object_name = 'document'

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        missions = user_position.managed_sfr_list
        return HandlingRequestDocument.objects.filter(
            handling_request__in=missions)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'History of S&F Request Document',
            'icon': 'fa-history',
        }

        context['metacontext'] = metacontext
        return context
