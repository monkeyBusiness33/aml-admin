from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalReadView
from django.db.models import Q, Case, When, F, Value, IntegerField
from django.db.models.functions import Cast, Concat
from django.urls import reverse_lazy

from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button
from handling.forms.sfr_documents import HandlingRequestDocumentForm
from handling.models import HandlingRequestDocument
from mission.forms.mission_documents import MissionDocumentForm


class MissionDocumentsListAjaxMixin(CustomAjaxDatatableView):
    model = HandlingRequestDocument
    search_values_separator = '+'
    initial_order = [["pk", "desc"], ]

    mission = None

    disable_queryset_optimization_only = True
    # TODO: Optimize more
    prefetch_related = {
        'created_by',
        'created_by__details',
        'files',
        'files__signed_by',
        'mission_leg',
        'mission_leg__departure_location',
        'mission_leg__departure_location__details',
        'mission_leg__departure_location__airport_details',
        'mission_leg__arrival_location',
        'mission_leg__arrival_location__details',
        'mission_leg__arrival_location__airport_details',
        'handling_request',
        'handling_request__mission_turnaround',
        'handling_request__mission_turnaround__mission_leg',
        'handling_request__mission_turnaround__mission_leg__mission',
        'handling_request__mission_turnaround__mission_leg__arrival_location',
        'handling_request__mission_turnaround__mission_leg__arrival_location__airport_details',
        'handling_request__mission_turnaround__mission_leg__next_leg',
    }

    def get_initial_queryset(self, request=None):
        type_q = Q()
        if request.app_mode == 'dod_portal':
            type_q = Q(is_dod_viewable=True)

        qs = HandlingRequestDocument.objects.filter(
            type_q,
            Q(mission=self.mission) |
            Q(mission_leg__mission=self.mission) |
            Q(handling_request__mission_turnaround__mission_leg__mission=self.mission)
        )
        qs = qs.annotate(
            sorting_index=Case(
                When(mission__isnull=False, then=Value(1)),
                When(mission_leg__isnull=False, then=Cast(Concat(
                    Cast(F('mission_leg__sequence_id'), IntegerField()),
                    Cast(Value('100000'), IntegerField()),
                    output_field=IntegerField()
                ), IntegerField())
                     ),
                When(handling_request__isnull=False, then=Cast(Concat(
                    Cast(F('handling_request__mission_turnaround__mission_leg__sequence_id'), IntegerField()),
                    Cast(Value('1000'), IntegerField()),
                    Cast(F('id'), IntegerField()),
                    output_field=IntegerField()
                ), IntegerField())
                     ),
                output_field=IntegerField()
            )
        )
        return qs

    def sort_queryset(self, params, qs):
        if len(params['orders']):
            if params['orders'][0].column_link.name == 'pk':
                # Default ordering found, use custom instead
                qs = qs.order_by('sorting_index')
            else:
                # Order by selected column
                qs = qs.order_by(*[order.get_order_mode() for order in params['orders']])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, },
        {'name': 'applicability', 'title': 'Applicability', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False, 'width': '30px', },
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
        row['applicability'] = obj.applicability
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
                                                           'admin:missions_documents_history',
                                                           kwargs={'pk': obj.pk}),
                                                       button_class='fa-history',
                                                       button_active=self.request.user.has_perm('handling.p_view'),
                                                       button_modal=True,
                                                       modal_validation=False)

        update_btn = get_datatable_actions_button(button_text='',
                                                  button_popup='Update Document',
                                                  button_url=reverse_lazy(
                                                      'admin:missions_documents_update',
                                                      kwargs={'pk': obj.pk}),
                                                  button_class='fa-edit',
                                                  button_active=self.request.user.has_perm('handling.p_update'),
                                                  button_modal=True,
                                                  modal_validation=True)

        row['actions'] = download_btn + update_btn + history_btn
        return


class MissionDocumentCreateMixin(BSModalCreateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = MissionDocumentForm
    success_message = 'Document successfully created'

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        request_person = getattr(self.request.user, 'person')

        instance = self.model(
            created_by=request_person,
            is_staff_added=self.request.user.is_staff,
        )
        kwargs.update({
            'instance': instance,
            'mission': self.mission,
        })

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create Mission Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


class MissionDocumentUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequestDocument
    form_class = HandlingRequestDocumentForm
    success_message = 'Document successfully updated'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Update Mission Document',
            'icon': 'fa-file-upload',
        }

        context['metacontext'] = metacontext
        return context


class MissionDocumentHistoryMixin(BSModalReadView):
    template_name = 'handling_request/43_document_history_modal.html'
    model = HandlingRequestDocument
    context_object_name = 'document'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'History of Mission Document',
            'icon': 'fa-history',
        }

        context['metacontext'] = metacontext
        return context
