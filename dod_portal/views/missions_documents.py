from django.db.models import Q
from django.http import Http404
from django.urls import reverse_lazy

from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button
from dod_portal.mixins import DodPermissionsMixin
from handling.models import HandlingRequestDocument
from mission.models import Mission
from mission.views_shared.mission_documents import MissionDocumentsListAjaxMixin, MissionDocumentCreateMixin, \
    MissionDocumentUpdateMixin, MissionDocumentHistoryMixin
from mission.views_shared.mission_packet_pdf import MissionPacketPdfMixin


class MissionDocumentsListAjaxView(DodPermissionsMixin, MissionDocumentsListAjaxMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list()
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except Mission.DoesNotExist:
            raise Http404

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, },
        {'name': 'applicability', 'title': 'Applicability', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False, 'width': '30px', },
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
        row['applicability'] = obj.applicability
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

        history_btn = ''
        if obj.files.filter(is_recent=False).exists():
            history_btn = get_datatable_actions_button(button_text='',
                                                       button_popup='Document History',
                                                       button_url=reverse_lazy(
                                                           'dod:missions_documents_history',
                                                           kwargs={'pk': obj.pk}),
                                                       button_class='fa-history',
                                                       button_active=True,
                                                       button_modal=True,
                                                       modal_validation=False)

        update_btn = get_datatable_actions_button(button_text='',
                                                  button_popup='Update Document',
                                                  button_url=reverse_lazy(
                                                      'dod:missions_documents_update',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-edit',
                                                  button_active=not obj.is_staff_added,
                                                  button_modal=True,
                                                  modal_validation=True)

        row['actions'] = download_btn + update_btn + history_btn
        return


class MissionDocumentCreateView(DodPermissionsMixin, MissionDocumentCreateMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list(managed=True)
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except Mission.DoesNotExist:
            raise Http404


class MissionDocumentUpdateView(DodPermissionsMixin, MissionDocumentUpdateMixin):
    def get_queryset(self):
        missions = self.person_position.get_missions_list(managed=True)
        qs = HandlingRequestDocument.objects.filter(
            Q(mission__in=missions) |
            Q(mission_leg__mission__in=missions) |
            Q(handling_request__mission_turnaround__mission_leg__mission__in=missions)
        )
        return qs

    def has_permission(self):
        document = self.get_object()
        if document.is_staff_added:
            return False
        return True


class MissionDocumentHistoryView(DodPermissionsMixin, MissionDocumentHistoryMixin):
    def get_queryset(self):
        missions = self.person_position.get_missions_list()
        qs = HandlingRequestDocument.objects.filter(
            Q(mission__in=missions) |
            Q(mission_leg__mission__in=missions) |
            Q(handling_request__mission_turnaround__mission_leg__mission__in=missions)
        )
        return qs


class MissionPacketPdfView(DodPermissionsMixin, MissionPacketPdfMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        missions = self.person_position.get_missions_list()
        try:
            self.mission = missions.get(pk=self.kwargs.get('pk'))
        except Mission.DoesNotExist:
            raise Http404
