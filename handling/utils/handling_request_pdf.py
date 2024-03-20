from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.text import slugify
from weasyprint import HTML


def generate_handling_request_pdf(handling_request, return_raw_pdf_file=False):
    """
    Generate S&F Request Details file
    :param handling_request:
    :param return_raw_pdf_file: Returns raw PDF file to continue working with it
    :return:
    """

    # Generate PDF
    static_path = f'file://{settings.BASE_DIR}/app/static'
    pdf_templates_path = f'file://{settings.BASE_DIR}/handling/templates/handling_request_pdf'

    if handling_request.customer_organisation_id == 100006 or return_raw_pdf_file:
        template_name = 'handling_request_pdf/pdf_v2.html'
    else:
        template_name = 'handling_request_pdf/pdf_v1.html'

    # Calculate tables rows to correct page breaking
    pax_count = handling_request.passengers_count or 4
    cargo_count = handling_request.cargo_payloads.count() or 6

    context = {
        'handling_request': handling_request,
        'passengers_payload_range': range(0, pax_count),
        'cargo_payloads_range': range(0, cargo_count),
        'static_path': static_path,
        'pdf_templates_path': pdf_templates_path,
    }

    template_string = render_to_string(template_name, context)
    html = HTML(string=template_string)
    main_doc = html.render()
    pdf = main_doc.write_pdf()
    pdf_file = BytesIO(pdf)
    if return_raw_pdf_file:
        return pdf_file
    pdf_content = pdf_file.getvalue()

    document_name = '{callsign}_{location}_{date}.pdf'.format(
        callsign=handling_request.callsign,
        location=slugify(handling_request.location_tiny_repr).upper(),
        date=handling_request.arrival_movement.date.strftime("%d%b%Y").upper()
    )
    file_dict = {
        'name': document_name,
        'content': pdf_content,
        'type': 'application/pdf',
    }

    return file_dict
