from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from core.forms import ConfirmationForm
from core.models import CommentReadStatus
from handling.models import HandlingRequest, HandlingRequestCrew
from handling.utils.handling_request_pdf import generate_handling_request_pdf
from user.mixins import AdminPermissionsMixin


class HandlingRequestsDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'handling_request/00_handling_request.html'
    model = HandlingRequest
    context_object_name = 'handling_request'
    permission_required = ['handling.p_view']

    def get_queryset(self):
        queryset = HandlingRequest.objects.detailed_list(
            include_test_requests=self.request.user.is_superuser).select_related(
            'customer_organisation',
            'customer_organisation__details',
            'handling_agent',
            'handling_agent__details',
            'airport',
            'airport__airport_details',
            'assigned_mil_team_member',
            'auto_spf',
            'fuel_booking__ipa__details',
        ).prefetch_related(
            'movement',
            'movement__airport__details',
            'movement__airport__airport_details',
            'movement__direction',
            'movement__hr_services',
            'movement__hr_services__service',
            'documents',
            'chat_conversations',
            'fuel_unit',
            'activity_log',
            'spf_v2',
            'comments',
            'sfr_ops_checklist_items',
            Prefetch(
                'comments__read_statuses',
                queryset=CommentReadStatus.objects.filter(person=self.request.user.person),
            ),
            Prefetch(
                'mission_crew',
                queryset=HandlingRequestCrew.objects.select_related('person', 'person__details'),
            )
        )

        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['retrospective_datetime_now'] = timezone.now()
        return context


class HandlingRequestDetailsPDFView(AdminPermissionsMixin, View):
    permission_required = ['handling.p_view']

    def get(self, request, *args, **kwargs):
        handling_request = HandlingRequest.objects.include_payload_data().get(pk=self.kwargs['pk'])
        document_file = generate_handling_request_pdf(handling_request)
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={document_file["name"]}'
        return response


class HandlingRequestAutoSPFPDFView(AdminPermissionsMixin, View):
    permission_required = ['handling.p_view']

    def get(self, request, *args, **kwargs):
        handling_request = HandlingRequest.objects.get(pk=self.kwargs['pk'])
        document_file = handling_request.get_spf_pdf()
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={document_file["name"]}'
        return response


class HandlingRequestCachePurgeView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = ConfirmationForm
    permission_required = ['handling.p_view']

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Purge S&F Request Cache',
            'icon': 'fa-hdd',
            'text': 'Please confirm cache purging. <ul>'
                    '<li>It will purge cache only related to the current S&F Request.</li>'
                    '<li>It will not have a destructive effect but next page refresh will take a bit longer.</li>'
                    '<li>It helps update statuses after manual database changes (GH, Fuel, SPF)</li></ul>',
            'action_button_text': 'Purge Cache',
            'action_button_class': 'btn-success',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            self.handling_request.invalidate_cache()
        return super().form_valid(form)
