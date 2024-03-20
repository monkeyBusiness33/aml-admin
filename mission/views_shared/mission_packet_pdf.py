from bootstrap_modal_forms.mixins import is_ajax
from django.http import HttpResponse
from django.views.generic import FormView

from handling.models import HandlingRequestDocument
from mission.forms.mission_packet_pdf import MissionPacketPdfForm
from mission.utils.mission_packet_pdf import generate_mission_packet_pdf


class MissionPacketPdfMixin(FormView):
    template_name = 'mission_packet_pdf_page.html'
    form_class = MissionPacketPdfForm

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mission': self.mission})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mission'] = self.mission
        return context

    def form_valid(self, form):
        mission_documents = form.cleaned_data['mission_documents']
        flight_legs_documents = form.cleaned_data['flight_legs_documents']
        turnaround_documents = form.cleaned_data['turnaround_documents']

        selected_documents_ids = mission_documents + flight_legs_documents + turnaround_documents
        documents_to_include = HandlingRequestDocument.objects.filter(pk__in=selected_documents_ids)

        if not is_ajax(self.request.META):
            document_file = generate_mission_packet_pdf(mission=self.mission, documents_to_include=documents_to_include)
            response = HttpResponse(document_file['content'], content_type=document_file['type'])
            response['Content-Disposition'] = f'attachment; filename={document_file["name"]}'
            return response

        return super().form_valid(form)
