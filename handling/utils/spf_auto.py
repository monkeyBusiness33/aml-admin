from io import BytesIO
from celery import shared_task
from datetime import datetime
from django.conf import settings
from django.db.models import Case, When, Value, BooleanField, Q
from django.template.loader import render_to_string
from weasyprint import HTML
from core.tasks import send_email
from handling.models import HandlingService, HandlingRequestServices, AutoServiceProvisionForm, HandlingRequest, \
    HandlingRequestAmendmentSession
from organisation.models import DLAContractLocation, EmailFunction
from user.models import Person


@shared_task()
def generate_auto_spf(handling_request, save_pdf=True):
    if not isinstance(handling_request, HandlingRequest):
        handling_request = HandlingRequest.objects.filter(pk=handling_request).first()

    requested_services = HandlingService.objects.filter(hr_services__movement__in=handling_request.movement.all())
    all_spf_services = HandlingService.objects.filter(is_active=True,
                                                      is_dla=True,
                                                      custom_service_for_request__isnull=True,
                                                      is_spf_visible=True,
                                                      )

    custom_services_max_count = 6
    custom_services = HandlingService.objects.filter(
        hr_services__movement__in=handling_request.movement.all(),
        custom_service_for_request=handling_request,
    )

    custom_services_list = []
    if custom_services.exists():
        absent_services = custom_services_max_count - custom_services.count()
        custom_services_list = list(custom_services)
        for i in range(absent_services):
            custom_services_list.append(None)

    always_requested_pks = [32, 38, ]
    always_requested_non_germany_pks = []

    if not handling_request.airport.details.country.code == 'DE':
        always_requested_non_germany_pks = [3, ]

    spf_services = all_spf_services.annotate(
        is_requested=Case(
            # Tick requested services and their "Representation Services"
            When(Q(pk__in=requested_services) | Q(represent__service_id__in=requested_services), then=Value(True)),
            # Tick "Always Requested" services
            When(pk__in=always_requested_pks, then=Value(True)),
            # Include non-Germany specific services
            When(pk__in=always_requested_non_germany_pks, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).exclude(
        (Q(represent__service_id__in=requested_services) & Q(is_requested=False))
    ).distinct()

    # Generate PDF
    static_path = f'file://{settings.BASE_DIR}/app/static/'
    template_name = 'pdf/auto_spf/default.html'

    # Determine Logo path
    logo_path = f'{static_path}assets/img/aml_logo_simple_65.png'
    ground_handler = getattr(handling_request, 'handling_agent', None)
    if ground_handler and ground_handler.ops_details:
        if not ground_handler.ops_details.spf_use_aml_logo and ground_handler.logo_motto.logo:
            logo_path = ground_handler.logo_motto.logo.url

    custom_services_count = 6 if len(custom_services_list) > 0 else 0
    services_count = spf_services.count() + custom_services_count

    context = {
        'handling_request': handling_request,
        'requested_services': spf_services,
        'date': datetime.now(),
        'custom_services': custom_services_list,
        'logo_path': logo_path,
        'base_dir': settings.BASE_DIR,
        'services_count': services_count,
    }

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


@shared_task
def generate_auto_spf_email(handling_request_id, requester_person_id, addresses_cc=None):
    if addresses_cc is None:
        addresses_cc = []
    addresses_bcc = []

    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()
    requester_person = Person.objects.filter(pk=requester_person_id).first()

    # Addresses TO
    addresses_to = handling_request.handling_agent.get_email_address()

    # Addresses CC and BCC
    addresses_cc.append('ops@amlglobal.net')
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_request')
    addresses_cc += email_function.get_addresses_cc(handling_request.handling_agent)
    addresses_bcc += email_function.get_addresses_bcc(handling_request.handling_agent)

    attachments = []
    requested_services = HandlingService.objects.filter(
        hr_services__movement__in=handling_request.movement.all(),
    ).distinct()

    handling_request_services = HandlingRequestServices.objects.filter(
        movement__in=handling_request.movement.all(),
    )

    is_hotel_transportation_requested = handling_request.movement.filter(
        hr_services__service__codename='transportation_hotel',
    ).exists()

    dla_contract = None
    if handling_request.fuel_required and hasattr(handling_request, 'fuel_booking'):
        if handling_request.fuel_booking.dla_contracted_fuel:
            dla_contract = DLAContractLocation.objects.get_handling_request_contract(handling_request).first()

    requester_position = requester_person.organisation_people.filter(
        organisation_id=100000000).first()

    # Stop execution in case if no any recipient available
    if not addresses_to and not addresses_cc and not addresses_bcc:
        handling_request.activity_log.create(
            author=requester_person,
            record_slug='sfr_handling_request_not_sent',
            details='Ground Handling Request has not been sent as no any recipient available',
        )
        return None

    subject = 'Ground Handling Request - {location} - {callsign} ({aircraft_designator}) - {arrival_date} / ' \
        '{departure_date}'.format(
            location=handling_request.location_short_repr,
            aircraft_designator=handling_request.aircraft_type.designator,
            callsign=handling_request.callsign,
            arrival_date=handling_request.arrival_movement.date.strftime("%Y-%m-%d"),
            departure_date=handling_request.departure_movement.date.strftime("%Y-%m-%d"),
        )

    body = render_to_string(
        template_name='email/spf_auto/spf_auto.html',
        context={
            'requester_person': requester_person,
            'requester_position': requester_position,
            'handling_request': handling_request,
            'handling_request_services': handling_request_services,
            'requested_services': requested_services,
            'dla_contract': dla_contract,
            'is_hotel_transportation_requested': is_hotel_transportation_requested,
        }
    )

    fuel_booking = getattr(handling_request, 'fuel_booking', None)
    if fuel_booking and fuel_booking.fuel_release:
        attachment = {
            'name': fuel_booking.fuel_release.file.name,
            'content': fuel_booking.fuel_release.read(),
            'type': 'application/pdf',
        }
        attachments.append(attachment)

    auto_spf_attachment = handling_request.get_spf_pdf()
    attachments.append(auto_spf_attachment)

    send_email(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )


@shared_task
def send_ground_handling_spf_amendment_email(amendment_session_id, requester_person_id, addresses_cc=None,
                                             departure_update_only=False):
    if addresses_cc is None:
        addresses_cc = []

    amendment_session = HandlingRequestAmendmentSession.objects.filter(pk=amendment_session_id).first()
    handling_request = amendment_session.handling_request
    requester_person = Person.objects.filter(pk=requester_person_id).first()

    # Addresses TO
    addresses_to = handling_request.handling_agent.get_email_address()

    # Addresses CC and BCC
    addresses_cc.append('ops@amlglobal.net')
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_request_amendment')
    addresses_cc += email_function.get_addresses_cc(handling_request.handling_agent)
    addresses_bcc = email_function.get_addresses_bcc(handling_request.handling_agent)

    attachments = []
    requester_position = requester_person.organisation_people.filter(
        organisation_id=100000000).first()

    # Stop execution in case if no any recipient available
    if not addresses_to and not addresses_cc:
        handling_request.activity_log.create(
            author=requester_person,
            record_slug='sfr_handling_request_not_sent',
            details='Ground Handling Request has not been sent as no any recipient available',
        )
        return None

    if departure_update_only:
        subject = 'Amendment to departure movement for {callsign} on {departure_date} at {location}'.format(
            callsign=amendment_session.get_callsign,
            departure_date=amendment_session.get_departure_date.strftime("%Y-%m-%d"),
            location=handling_request.airport.short_repr,
        )
    else:
        subject = 'Amendment to ground handling booking for {callsign} on {arrival_date} at {location}'.format(
            callsign=amendment_session.get_callsign,
            arrival_date=amendment_session.get_arrival_date.strftime("%Y-%m-%d"),
            location=handling_request.airport.short_repr,
        )

    body = render_to_string(
        template_name='email/spf_auto/spf_auto_amendment.html',
        context={
            'requester_person': requester_person,
            'requester_position': requester_position,
            'handling_request': handling_request,
            'amendment_session': amendment_session,
        }
    )

    fuel_booking = getattr(handling_request, 'fuel_booking', None)
    if fuel_booking and fuel_booking.fuel_release:
        attachment = {
            'name': fuel_booking.fuel_release.file.name,
            'content': fuel_booking.fuel_release.read(),
            'type': 'application/pdf',
        }
        attachments.append(attachment)

    auto_spf_attachment = handling_request.get_spf_pdf()
    attachments.append(auto_spf_attachment)

    send_email(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )

    # Close amendment session
    action = 'Departure Update' if departure_update_only else 'Handling Request Amendment'
    handling_request.activity_log.create(
        author=requester_person,
        record_slug='sfr_gh_amendment_sent',
        details=f'{action}: Email message has been sent',
    )


@shared_task
def send_ground_handling_spf_cancellation_email(handling_request_id, requester_person_id, addresses_cc=None):
    if addresses_cc is None:
        addresses_cc = []
    handling_request = HandlingRequest.objects.filter(pk=handling_request_id).first()
    requester_person = Person.objects.filter(pk=requester_person_id).first()

    # Addresses TO
    ground_handler = getattr(handling_request.auto_spf, 'sent_to')
    addresses_to = ground_handler.get_email_address()

    # Addresses CC and BCC
    addresses_cc.append('ops@amlglobal.net')
    email_function, created = EmailFunction.objects.get_or_create(codename='ground_handling_request_cancellation')
    addresses_cc += email_function.get_addresses_cc(handling_request.handling_agent)
    addresses_bcc = email_function.get_addresses_bcc(handling_request.handling_agent)

    attachments = []
    requester_position = requester_person.organisation_people.filter(
        organisation_id=100000000).first()

    # Stop execution in case if no any recipient available
    if not addresses_to and not addresses_cc and not addresses_bcc:
        handling_request.activity_log.create(
            author=requester_person,
            record_slug='sfr_gh_amendment_not_sent',
            details='Ground Handling Request cancellation has not been sent as no any recipient available',
        )
        return None

    subject = 'Cancellation of ground handling booking for {callsign} on {arrival_date} at {location}'.format(
        callsign=handling_request.callsign,
        arrival_date=handling_request.arrival_movement.date.strftime("%Y-%m-%d"),
        location=handling_request.airport.short_repr,
    )

    body = render_to_string(
        template_name='email/spf_auto/spf_auto_cancellation.html',
        context={
            'requester_person': requester_person,
            'requester_position': requester_position,
            'handling_request': handling_request,
        }
    )

    send_email.delay(
        subject=subject,
        body=body,
        recipient=addresses_to,
        cc=addresses_cc,
        bcc=addresses_bcc,
        attachments=attachments,
    )
