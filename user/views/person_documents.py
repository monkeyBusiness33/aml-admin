from ajax_datatable import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from bootstrap_modal_forms.mixins import PassRequestMixin
from django.http import Http404, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_clipped_value, get_datatable_actions_button
from user.forms import TravelDocumentForm
from user.mixins import AdminPermissionsMixin
from user.models import TravelDocument, TravelDocumentFile, Person


class PersonTravelDocumentsAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = TravelDocument
    search_values_separator = '+'
    length_menu = [[10, 25, 50, 100, ], [10, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return TravelDocument.objects.filter(person_id=self.kwargs['pk'])

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'type', 'title': 'Type', 'foreign_field': 'type__name', 'visible': True, 'width': '20px'},
        {'name': 'start_date', 'visible': True, 'width': '20px'},
        {'name': 'end_date', 'visible': True, 'width': '20px'},
        {'name': 'issue_country', 'title': 'Issue Country', 'foreign_field': 'issue_country__name',
         'visible': True, 'width': '380px', },
        {'name': 'is_current', 'visible': True, 'searchable': False, },
        {'name': 'comments', 'visible': True, 'searchable': False, },
        {'name': 'attachments', 'title': 'attachments', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['start_date'] = obj.start_date.strftime("%Y-%m-%d") if obj.start_date else ''
        row['end_date'] = obj.end_date.strftime("%Y-%m-%d") if obj.end_date else ''
        row['comments'] = get_datatable_clipped_value(text=obj.comments, max_length=150)

        document_files = []
        for document_file in obj.files.all():
            btn = get_datatable_actions_button(button_text='',
                                               button_url=document_file.file.url,
                                               button_class='fa-file-download',
                                               button_active=self.request.user.has_perm('core.p_contacts_view'),
                                               button_popup=f'Download {document_file.file.name}',
                                               button_modal=False,
                                               modal_validation=False)
            document_files.append(btn)
        document_files_html = ''.join(map(str, document_files))

        update_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:person_travel_document_update',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-edit',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_popup='Update',
                                                  button_modal_size='#modal-lg',
                                                  button_modal=True,
                                                  modal_validation=False)

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:person_travel_document_delete',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_popup='Delete',
                                                  button_modal=True,
                                                  modal_validation=False)

        row['attachments'] = document_files_html
        row['actions'] = update_btn + delete_btn
        return


class TravelDocumentCreateView(AdminPermissionsMixin, BSModalCreateView):
    template_name = 'person_document_modal.html'
    model = TravelDocument
    form_class = TravelDocumentForm
    success_message = 'Document added successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        person_id = self.kwargs.get('pk')

        instance = self.model(
            person_id=person_id,
            type_id=1,
        )

        kwargs.update({'instance': instance})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Travel Document',
            'icon': 'fa-file',
        }

        context['metacontext'] = metacontext
        return context


class TravelDocumentUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'person_document_modal.html'
    model = TravelDocument
    form_class = TravelDocumentForm
    success_message = 'Document updated successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Update Travel Document',
            'icon': 'fa-file',
        }

        context['metacontext'] = metacontext
        return context


class TravelDocumentDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = TravelDocument
    form_class = ConfirmationForm
    success_message = 'Document deleted successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Travel Document',
            'icon': 'fa-file',
            'text': f'Please confirm deleting this document along with all attached files',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Delete',
        }

        context['metacontext'] = metacontext
        return context


class TravelDocumentFileDeleteView(AdminPermissionsMixin, PassRequestMixin, FormView):
    form_class = ConfirmationForm
    permission_required = ['core.p_contacts_update']
    document_file = None
    travel_document = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.document_file = TravelDocumentFile.objects.get(pk=self.kwargs['document_file_id'])
            self.travel_document = getattr(self.document_file, 'travel_document')
        except TravelDocumentFile.DoesNotExist:
            raise Http404

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        self.document_file.delete()
        self.travel_document.updated_by = request_person
        self.travel_document.save()
        return JsonResponse({'success': 'true'})


class PersonTravelDocumentStatusMixin(View):
    person = None

    def get(self, request, *args, **kwargs):
        resp = dict()
        resp['status_light_html'] = self.person.travel_document_status_light

        current_travel_document = getattr(self.person, 'current_travel_document', None)
        files_download_icons = ''
        if current_travel_document:
            files_download_icons = current_travel_document.get_files_download_icons()
        resp['files_download_icons'] = files_download_icons

        return JsonResponse(resp)


class PersonTravelDocumentStatusView(PersonTravelDocumentStatusMixin, AdminPermissionsMixin):
    permission_required = []

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.person = Person.objects.get(pk=self.kwargs['person_id'])
        except Person.DoesNotExist:
            raise Http404
