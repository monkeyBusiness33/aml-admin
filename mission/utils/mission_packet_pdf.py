from io import BytesIO

from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.template.loader import render_to_string
from pypdf import PdfMerger
from weasyprint import HTML

from handling.models import HandlingRequestDocument, HandlingRequestDocumentFile, HandlingRequest
from handling.utils.handling_request_pdf import generate_handling_request_pdf
from mission.models import Mission, MissionLegPassengersPayload, MissionLegCargoPayload


def generate_mission_packet_pdf(mission: Mission, documents_to_include=None):
    """
    Generate S&F Request Details file
    :param mission: Mission instance
    :param documents_to_include: Documents to include to the Packet
    :return:
    """
    if documents_to_include is None:
        documents_to_include = []
    static_path = f'file://{settings.BASE_DIR}/app/static'
    pdf_templates_path = f'file://{settings.BASE_DIR}/mission/templates/mission_packet_pdf'
    template_name = 'mission_packet_pdf/mission_summary.html'

    # Documents
    recent_file_qs = HandlingRequestDocumentFile.objects.filter(document_id=OuterRef('pk')).values('file')
    documents_qs = HandlingRequestDocument.objects.annotate(
        recent_file_ext=Subquery(recent_file_qs[:1]),
    ).filter(
        recent_file_ext__iendswith='.pdf',
        pk__in=documents_to_include,
    )

    # Payload
    passengers_payload = MissionLegPassengersPayload.objects.filter(mission_legs__mission=mission).prefetch_related(
        'mission_legs',
    ).distinct()
    cargo_payload = MissionLegCargoPayload.objects.filter(mission_legs__mission=mission).prefetch_related(
        'mission_legs',
    ).distinct()
    pax_count = passengers_payload.count() or 5
    cargo_count = cargo_payload.count() or 2

    flight_legs_header_width = mission.active_legs.count() * 20
    if flight_legs_header_width < 80:
        flight_legs_header_width = 80

    context = {
        'mission': mission,
        'passengers_payload': passengers_payload,
        'cargo_payload': cargo_payload,
        'passengers_payload_range': range(0, pax_count),
        'cargo_payloads_range': range(0, cargo_count),
        'flight_legs_header_width': flight_legs_header_width,
        'static_path': static_path,
        'pdf_templates_path': pdf_templates_path,
    }

    template_string = render_to_string(template_name, context)
    mission_summary_pdf_bytes = HTML(string=template_string).write_pdf()
    mission_summary_pdf_file = BytesIO(mission_summary_pdf_bytes)

    merger = PdfMerger()
    merger.append(mission_summary_pdf_file)

    # Attach mission-wide documents
    for document in documents_qs.filter(mission=mission):
        merger.append(document.recent_file.file)

    for mission_leg in mission.active_legs:
        # Attach Flight Leg documents
        for document in documents_qs.filter(mission_leg=mission_leg):
            merger.append(document.recent_file.file)

        handling_request = HandlingRequest.objects.include_payload_data().with_eta_etd_and_status_index().filter(
            mission_turnaround__mission_leg=mission_leg).first()
        if handling_request:
            # Attach S&F Request PDF if available
            if handling_request.is_pdf_available:
                handling_request_pdf_file = generate_handling_request_pdf(
                        handling_request=handling_request, return_raw_pdf_file=True)
                merger.append(handling_request_pdf_file)

            # Attach Fuel Release if available
            if hasattr(handling_request, 'fuel_booking') \
                and not handling_request.fuel_booking.fuel_release.name == '' \
                    and handling_request.fuel_booking.fuel_release.name.endswith('.pdf'):
                fuel_release = handling_request.fuel_booking.fuel_release
                merger.append(fuel_release)

            # Attach S&F Request related documents
            for document in documents_qs.filter(handling_request=handling_request):
                merger.append(document.recent_file.file)

    output = BytesIO()
    merger.write(output)
    pdf_content = output.getvalue()

    document_name = 'mission_packet_{mission_number}.pdf'.format(
        mission_number=mission.mission_number_repr,
    )
    file_dict = {
        'name': document_name,
        'content': pdf_content,
        'type': 'application/pdf',
    }

    return file_dict
