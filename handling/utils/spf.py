from django.utils.text import slugify

from ..models import HandlingService
from io import BytesIO
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML


def create_spf_document(spf, save_file: bool = True):
    static_path = f'file://{settings.BASE_DIR}/app/static'
    template_name = 'pdf/spf/default.html'
    pdf_templates_path = f'file://{settings.BASE_DIR}/handling/templates/pdf'

    context = {
        'spf': spf,
        'dla_services': spf.dla_services_list,
        'custom_services': spf.custom_services_list,
        'static_path': static_path,
        'pdf_templates_path': pdf_templates_path,
    }

    template_string = render_to_string(template_name, context)
    html = HTML(string=template_string)
    main_doc = html.render()
    pdf = main_doc.write_pdf()
    pdf_file = BytesIO(pdf)
    pdf_content = pdf_file.getvalue()
    spf_document_name = 'SPF_for_{callsign}_{location}_{spf_id}.pdf'.format(
        callsign=spf.handling_request.callsign,
        location=slugify(spf.handling_request.location_full_repr),
        spf_id=spf.id,
    )

    if save_file:
        # Save file to S3 storage
        spf.spf_document.save(spf_document_name, pdf_file)
        spf.skip_signal = True
        spf.save()

    spf_document_file = {
        'name': spf_document_name,
        'content': pdf_content,
        'type': 'application/pdf',
    }

    return spf_document_file
