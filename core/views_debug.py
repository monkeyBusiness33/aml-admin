# from weasyprint import HTML
from tempfile import NamedTemporaryFile

from django.http import HttpResponse
# from io import BytesIO
# from django.template.loader import get_template
# from django.template.loader import render_to_string
# from django.conf import settings
from django.views.generic.base import TemplateView
from handling.models import HandlingRequest, HandlingRequestDocument
from handling.utils.document_signing import sign_document
from handling.utils.handling_request_pdf import generate_handling_request_pdf
from mission.models import Mission


# from handling.models import HandlingService, ServiceProvisionForm
# from handling.utils.spf import create_spf_document


# class SPFPDFView(TemplateView):
#     '''
#     Debugging view for the SPF PDF generator
#     Available on the /ops/debug/spf/ uri in DEBUG mode.
#     '''
#     template_name = 'pdf/spf/default.html'

#     def get(self, request, *args, **kwargs):
#         spf = ServiceProvisionForm.objects.get(pk=self.kwargs['pk'])
#         document_file = create_spf_document(spf, False)
#         pdf = document_file['content']

#         response = HttpResponse(pdf, content_type='application/pdf')
#         #Download as attachment
#         # response['Content-Disposition'] = 'attachment; filename=test.pdf'
#         # Display in browser
#         response['Content-Disposition'] = 'inline; test.pdf'
#         return response


class AutoSPFPDFView(TemplateView):
    """
    Debugging view for the AutoSPF PDF generator
    Available on the /ops/debug/auto_spf/ uri in DEBUG mode.
    """
    template_name = 'pdf/auto_spf/default.html'

    def get(self, request, *args, **kwargs):
        handling_request = HandlingRequest.objects.get(pk=self.kwargs['handling_request_id'])
        document_file = handling_request.get_spf_pdf()
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; test.pdf'
        return response


class HandlingRequestDetailsPDFView(TemplateView):
    """
    Available on the /ops/debug/handling_request_pdf/<handling_request_id>/ uri in DEBUG mode.
    """
    template_name = 'pdf/auto_spf/default.html'

    def get(self, request, *args, **kwargs):
        handling_request = HandlingRequest.objects.include_payload_data().get(pk=self.kwargs['handling_request_id'])
        document_file = generate_handling_request_pdf(handling_request)
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; test.pdf'
        return response


class MissionPacketPDFView(TemplateView):
    """
    Available on the /ops/debug/mission_packet_pdf/<mission_id>/ uri in DEBUG mode.
    """
    template_name = 'pdf/auto_spf/default.html'

    def get(self, request, *args, **kwargs):
        mission = Mission.objects.include_details().get(pk=self.kwargs['mission_id'])
        from mission.utils.mission_packet_pdf import generate_mission_packet_pdf
        document_file = generate_mission_packet_pdf(mission)
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; test.pdf'
        return response


class SignHandlingRequestDocumentView(TemplateView):
    """
    Available on the /ops/debug/sign_handling_request_document/<document_id>/ uri in DEBUG mode.
    """
    template_name = 'pdf/auto_spf/default.html'

    def get(self, request, *args, **kwargs):
        handling_request_document = HandlingRequestDocument.objects.get(pk=self.kwargs['document_id'])

        sign = open(f".dev/sign.png", "rb")
        sign_bytes = sign.read()

        sign_temp = NamedTemporaryFile(suffix='.png')
        sign_temp.write(sign_bytes)
        sign_temp.seek(0)

        document_file = sign_document(signature=sign_temp,
                                      document=handling_request_document,
                                      author=request.user.person)
        pdf = document_file['content']

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; test.pdf'
        return response
