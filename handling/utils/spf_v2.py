from datetime import datetime
from io import BytesIO

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from sql_util.aggregates import Exists
from weasyprint import HTML


def handling_request_create_or_update_spf_v2(handling_request):
    from handling.models import HandlingRequestSpf, HandlingRequestSpfService, HandlingService
    from organisation.models import DlaService

    # Skip processing for old S&F Requests
    if handling_request.is_legacy_spf_v1:
        return None

    # Create SPF V2
    spf_v2, created = HandlingRequestSpf.objects.get_or_create(handling_request=handling_request)

    if spf_v2.is_reconciled:
        return None

    # Get DLA services for auto-select
    dla_services = DlaService.objects.get_applicable_services(handling_request.handling_agent)
    dla_service_to_update = []

    # Assign DLA services to the SPF
    for dla_service in dla_services:

        is_pre_ticked = False
        if dla_service.is_pre_ticked:
            is_pre_ticked = True

        if dla_service.is_handler_auto_select:
            if all([not dla_service.applies_after_minutes, not dla_service.applies_if_pax_onboard,
                    not dla_service.applies_if_cargo_onboard]):
                is_pre_ticked = True

            elif dla_service.applies_after_minutes and dla_service.applies_after_minutes < handling_request.ete_minutes:
                is_pre_ticked = True

            elif dla_service.applies_if_pax_onboard and handling_request.is_pax_on_board:
                is_pre_ticked = True

            elif dla_service.applies_if_cargo_onboard and handling_request.is_cargo_on_board:
                is_pre_ticked = True

        # HandlingRequestSpfService.objects.update_or_create(
        #     spf=spf_v2,
        #     dla_service=dla_service,
        #     defaults={
        #         'is_pre_ticked': is_pre_ticked,
        #     }
        # )

        # Optimized way to create or update all services in SPF
        obj = HandlingRequestSpfService(
            spf=spf_v2,
            dla_service=dla_service,
            is_pre_ticked=is_pre_ticked,
        )
        dla_service_to_update.append(obj)

    HandlingRequestSpfService.objects.bulk_create(
        dla_service_to_update,
        update_conflicts=True,
        unique_fields=['spf', 'dla_service'],
        update_fields=['is_pre_ticked'],
    )

    handling_services_qs = HandlingService.objects.active().annotate(
        is_requested=Exists('hr_services', filter=Q(movement__request=handling_request)),
    ).filter(
        (Q(hr_services__movement__request=handling_request) & Q(is_spf_v2_visible=True)) |
        # Include non-DLA services like "Ramp Transportation"
        (Q(is_spf_v2_non_dla=True) & Q(is_spf_v2_visible=True))
    ).distinct()

    sfr_handling_services_to_update = handling_services_qs.filter(~Q(dla_service__in=dla_services))
    sfr_dla_services_to_update = handling_services_qs.filter(Q(dla_service__isnull=False))

    for handling_request_service in sfr_handling_services_to_update | sfr_dla_services_to_update:
        if handling_request_service.dla_service_id:
            filter_q = {'dla_service_id': handling_request_service.dla_service_id}
            value_q = {'handling_service_id': handling_request_service.pk}
        else:
            filter_q = {'handling_service_id': handling_request_service.pk}
            value_q = {'dla_service_id': handling_request_service.dla_service_id}

        HandlingRequestSpfService.objects.update_or_create(
            spf=spf_v2,
            **filter_q,
            defaults={
                'is_pre_ticked': handling_request_service.is_requested,
                **value_q,
            }
        )

    spf_services_to_deselect = HandlingRequestSpfService.objects.filter(
        ~Q(dla_service_id__in=sfr_dla_services_to_update.values_list('dla_service_id', flat=True)) &
        Q(dla_service_id__in=dla_services.filter(Q(is_handler_auto_select=False) & Q(is_pre_ticked=False))),
        spf=spf_v2,
    )

    spf_services_to_deselect.update(is_pre_ticked=False)

    spf_services_to_delete = HandlingRequestSpfService.objects.filter(
        spf=handling_request.spf_v2,
    ).filter(
        Q(
            ~Q(dla_service__in=dla_services) &
            ~Q(dla_service__in=sfr_dla_services_to_update.values_list('dla_service_id', flat=True)),
        ) &
        Q(
            ~Q(handling_service__in=sfr_handling_services_to_update.values_list('pk', flat=True)),
        )
    )

    spf_services_to_delete.delete()

    return handling_request


@shared_task()
def handling_request_generate_spf_v2_pdf(handling_request, save_pdf=True):
    from handling.models import HandlingRequest
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.filter(pk=handling_request).first()

    spf_services = handling_request.spf_v2.services.sorted().prefetch_related(
        'dla_service',
        'handling_service',
    )

    # Generate PDF
    static_path = f'file://{settings.BASE_DIR}/app/static/'
    template_name = 'pdf/spf_v2/default.html'

    # Determine Logo path
    logo_path = f'{static_path}assets/img/aml_logo_simple_65.png'
    ground_handler = getattr(handling_request, 'handling_agent', None)
    if ground_handler and ground_handler.ops_details:
        if not ground_handler.ops_details.spf_use_aml_logo and ground_handler.logo_motto.logo:
            logo_path = ground_handler.logo_motto.logo.url

    context = {
        'handling_request': handling_request,
        'requested_services': spf_services,
        'date': datetime.now(),
        'logo_path': logo_path,
        'base_dir': settings.BASE_DIR,
        'services_count': spf_services.count(),
    }

    # Mute debugging logs
    import weasyprint
    weasyprint.LOGGER.setLevel(50)

    template_string = render_to_string(template_name, context)
    html = HTML(string=template_string, base_url=static_path)
    main_doc = html.render()
    pdf = main_doc.write_pdf()
    pdf_file = BytesIO(pdf)
    pdf_content = pdf_file.getvalue()
    spf_document_name = 'SPF_for_{callsign}_{location}.pdf'.format(
        callsign=handling_request.callsign,
        location=handling_request.location_tiny_repr,
    )

    if save_pdf:
        from handling.models import AutoServiceProvisionForm
        auto_spf = getattr(handling_request, 'auto_spf', AutoServiceProvisionForm())
        auto_spf.handling_request = handling_request
        auto_spf.spf_document.save(spf_document_name, pdf_file)
        auto_spf.save()

    spf_document_file = {
        'name': spf_document_name,
        'content': pdf_content,
        'type': 'application/pdf',
    }

    return spf_document_file
