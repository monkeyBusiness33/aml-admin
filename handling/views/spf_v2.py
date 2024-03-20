from ajax_datatable.filters import build_column_filter
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax, PassRequestMixin
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_actions_button
from handling.forms.sfr_aircraft import HandlingRequestConfirmTailNumberForm
from handling.forms.sfr_spf_v2 import RequestSignedSpfForm, SignedSpfUploadForm
from handling.models import HandlingRequestSpfService, HandlingRequestSpf, HandlingRequest
from handling.utils.handler_notifications import send_signed_spf_request
from handling.utils.staff_notifications import notification_staff_signed_spf_uploaded
from user.mixins import AdminPermissionsMixin


class HandlingRequestSpfV2ServicesAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = HandlingRequestSpfService
    search_values_separator = '+'
    length_menu = [[25, 50, 100, 250, -1], [25, 50, 100, 250, 'all']]
    initial_order = [["is_pre_ticked", "desc"], ["name", "asc"]]
    permission_required = ['handling.p_view']

    # QuerySet Optimizations
    prefetch_related = {
        'spf__handling_request',
        'handling_service',
        'dla_service',
    }

    def get_initial_queryset(self, request=None):
        return HandlingRequestSpfService.objects.sorted().filter(spf__handling_request_id=self.kwargs['pk'])

    column_defs = [
        {'name': 'pk', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'name', 'visible': True, 'searchable': False, },
        {'name': 'is_pre_ticked', 'visible': True, 'searchable': False, 'className': 'text-center'},
        {'name': 'was_taken', 'visible': True, 'searchable': False, 'className': 'text-center'},
        {'name': 'comments', 'visible': True, 'searchable': False, },
    ]

    def customize_row(self, row, obj):
        user = getattr(self.request, 'user')
        is_editable = obj.spf.handling_request.is_spf_v2_editable and user.has_perm('handling.p_spf_v2_reconcile')

        def yes_no(value, output_string_yes, output_string_no):
            return output_string_yes if value else output_string_no

        row['is_pre_ticked'] = ('<input class="form-check-input update-value" type="checkbox" '
                                'value="1" id="{id}" {disabled} {checked}>').format(
            id=f'is_pre_ticked_{obj.pk}',
            disabled='disabled',
            checked=yes_no(obj.is_pre_ticked, 'checked', ''),
        )

        row['was_taken'] = ('<input class="form-check-input update-value" type="checkbox" data-href={url} '
                            'data-value-key="was_taken"'
                            'value="1" id="{id}" {disabled} {checked}>').format(
            id=f'was_taken_{obj.pk}',
            disabled='disabled' if obj.dla_service and obj.dla_service.is_always_selected or not is_editable else '',
            url=reverse_lazy('admin:handling_request_spf_v2_service_update', kwargs={'pk': obj.pk}),
            checked=yes_no(obj.was_taken, 'checked', ''),
        )

        row['comments'] = ('<input class="datatable-input update-value" type="text" data-index="1" placeholder="..."'
                           'data-href={url} data-value-key="comments" '
                           'value="{value}" maxlength="{maxlength}" {disabled}>').format(
            value=obj.comments or '',
            maxlength=obj._meta.get_field('comments').max_length,
            disabled='disabled' if not is_editable else '',
            url=reverse_lazy('admin:handling_request_spf_v2_service_update', kwargs={'pk': obj.pk}),
        )


class HandlingRequestSpfV2ServiceUpdateView(AdminPermissionsMixin, FormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['handling.p_spf_v2_reconcile']

    spf_service = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.spf_service = get_object_or_404(HandlingRequestSpfService, pk=self.kwargs['pk'])

    def form_valid(self, form, *args, **kwargs):
        # Get input data
        data_key = self.request.POST.get('dataKey')
        data_val = self.request.POST.get('dataVal')

        # Validate input data
        allowed_values_to_update = ['was_taken', 'comments', ]
        if data_key not in allowed_values_to_update:
            return JsonResponse({"errors": "Value disallowed to update"}, status=422)

        # Parse value
        if data_val in ['true', 'false']:
            data_val = True if data_val == 'true' else False

        # Set and save value
        setattr(self.spf_service, data_key, data_val)
        self.spf_service.save()

        return super().form_valid(form)


class HandlingRequestSpfV2ReconciledView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_confirm_tail_number.html'
    model = HandlingRequest
    form_class = HandlingRequestConfirmTailNumberForm
    permission_required = ['handling.p_spf_v2_reconcile']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        handling_request = self.get_object()
        if not hasattr(handling_request, 'spf_v2'):
            return Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'spf_reconcile': True})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'SPF Reconciled',
            'icon': 'fa-check',
            'action_button_text': 'Confirm',
            'action_button_class': 'btn-success',
            'alerts': [
                {
                    'text': 'Please confirm you wish to lock the SPF as reconciled. This action is not reversible.',
                    'class': 'alert-danger',
                    'icon': 'info',
                    'position': 'bottom',
                }
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        spf_file = form.cleaned_data['spf_file']
        if not is_ajax(self.request.META):
            if spf_file:
                sfr_document = form.instance.documents.create(
                    type_id=3,
                    description='Signed SPF File',
                    created_by=getattr(self, 'person'),
                    is_staff_added=True,
                )
                sfr_document.files.create(
                    file=spf_file,
                    uploaded_by=getattr(self, 'person'),
                    is_recent=True,
                )
            form.instance.spf_v2.is_reconciled = True
            form.instance.spf_v2.reconciled_by = getattr(self, 'person')
            form.instance.spf_v2.reconciled_at = timezone.now()
            form.instance.spf_v2.save()
            form.instance.activity_log.create(
                author=getattr(self, 'person'),
                record_slug='sfr_spf_reconciled',
                details='SPF reconciled'
            )
        return response


class SpfToReconcileAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = HandlingRequest
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    initial_order = [["etd_date", "desc"], ]
    permission_required = ['handling.p_spf_v2_reconcile']

    # QuerySet Optimizations
    prefetch_related = {
        'airport',
        'airport__details',
        'spf_v2',
    }

    def get_initial_queryset(self, request=None):
        qs = HandlingRequest.objects.spf_to_reconcile()
        return qs

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        search_filters = Q()

        for column_name in column_names:
            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            if column_name == 'location':
                return qs.filter(
                    Q(airport__airport_details__icao_code__icontains=search_value) |
                    Q(airport__airport_details__icao_code__icontains=search_value) |
                    Q(airport__details__registered_name__icontains=search_value)
                ).distinct()
            else:
                # Default behaviour for this function
                if self.search_values_separator and self.search_values_separator in search_value:
                    search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

                column_filter = build_column_filter(column_name, column_obj, column_spec, search_value,
                                                    global_filtering)
                if column_filter:
                    search_filters |= column_filter

                return qs.filter(search_filters)

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': True, 'width': '10px', },
        {'name': 'callsign', 'visible': True, 'className': 'url_source_col', 'width': '150px', },
        {'name': 'location', 'title': 'Location', 'searchable': True, 'orderable': False, 'visible': True,
         'className': 'url_source_col', },
        {'name': 'etd_date', 'title': 'ETD (Z)', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': True, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False,
         'className': 'actions', 'width': '100px', },
    ]

    def customize_row(self, row, obj):
        row['callsign'] = f'<span data-url="{obj.get_absolute_url()}" data-target="_blank">{obj.callsign}</span>'
        row['etd_date'] = f'{obj.etd_date.strftime("%Y-%m-%d %H:%M")} UTC' if obj.etd_date else None
        row['location'] = f'<span data-url="{obj.airport.get_absolute_url()}">{obj.airport.short_repr}</span>'

        row['actions'] = get_datatable_actions_button(button_text='',
                                                      button_url=reverse_lazy(
                                                          'admin:handling_spf_reconcile',
                                                          kwargs={'pk': obj.spf_v2.pk}),
                                                      button_class='fas fa-clipboard-check',
                                                      button_active=self.request.user.has_perm(
                                                          'handling.p_spf_v2_reconcile'),
                                                      button_popup='SPF Reconciled',
                                                      button_modal_size='#modal-xxl',
                                                      button_modal=True,
                                                      modal_validation=True)


class SpfToReconcileView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_spf_v2_reconcile']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'SPFs to Reconcile',
            'page_id': 'spf_to_reconcile_page',
            'page_css_class': 'datatable-clickable',
            'datatable_uri': 'admin:handling_spf_to_reconcile_ajax',
            'css_files': [
                static('css/spf_to_reconcile.css'),
            ],
            'js_scripts': [
                static('js/spf_reconcile_modal.js'),
            ]
        }

        context['metacontext'] = metacontext
        return context


class SpfToReconcileModalView(AdminPermissionsMixin, TemplateView):
    template_name = 'handling_request/_modal_spf_reconcile.html'
    permission_required = ['core.p_spf_v2_reconcile']

    spf = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.spf = get_object_or_404(HandlingRequestSpf, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        details = '{callsign} - {location} - {handler} - {tail_number} - {etd}'.format(
            callsign=self.spf.handling_request.callsign,
            reference=self.spf.handling_request.reference,
            location=self.spf.handling_request.airport.short_repr,
            handler=self.spf.handling_request.handling_agent.full_repr,
            tail_number=self.spf.handling_request.tail_number or 'Not yet assigned',
            etd=self.spf.handling_request.departure_movement.date.strftime("%Y-%m-%d %H:%M"),
        )

        metacontext = {
            'title': f'Reconcile SPF: {details}',
            'icon': 'fa-clipboard-check',
            'page_id': 'spf_to_reconcile_page',
            'datatable_uri': 'admin:handling_spf_to_reconcile_ajax',
        }

        context['metacontext'] = metacontext
        context['spf'] = self.spf
        context['handling_request'] = self.spf.handling_request
        return context


class RequestSignedSpfView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = RequestSignedSpfForm
    permission_required = ['handling.p_request_signed_spf']

    handling_request = None
    handler_email_addresses = []

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])
        self.handler_email_addresses = self.handling_request.handling_agent.get_email_address()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'handler_email_addresses': self.handler_email_addresses,
            'handling_request': self.handling_request,
        })
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        handler_no_email_text = None
        if not self.handler_email_addresses:
            handler_no_email_text = '<b>{handler}</b> has no contact email address stored. Please enter the email' \
                                    ' address that the request should be sent to (this will be' \
                                    ' stored for future use)'.format(
                                        handler=self.handling_request.handling_agent.trading_or_registered_name)

        ground_handler = getattr(self.handling_request.handling_agent, 'full_repr')

        metacontext = {
            'form_id': 'request_signed_spf',
            'title': 'Request Signed SPF from Handler',
            'icon': 'fa-sticky-note',
            'text': f'Do you wish to send an auto-generated SPF request email to the'
                    f' <b>"{ ground_handler }"</b> ground handler?',
            'text_danger': handler_no_email_text,
            'action_button_text': 'Send',
        }

        if not self.handling_request.is_gh_signed_spf_request_can_be_sent:
            context['form'] = None
            metacontext['hide_action_button'] = True
            metacontext['text'] = None
            metacontext['text_danger'] = (f'An auto-generated SPF request has already sent to the '
                                          f'<b>"{ground_handler}"</b> ground handler.')

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        if not is_ajax(self.request.META):
            submitted_handler_emails = form.cleaned_data['handler_email']
            send_to_people_positions = form.cleaned_data['send_to_people']
            final_cc_list = []

            if submitted_handler_emails == ['']:
                submitted_handler_emails = []

            send_to_people_emails = []
            for position in send_to_people_positions:
                if position.contact_email:
                    send_to_people_emails.append(position.contact_email)

            # Update S&F Request Handler with given email address
            if not self.handler_email_addresses and submitted_handler_emails:
                handler_details = getattr(self.handling_request.handling_agent, 'handler_details')
                handler_details.contact_email = submitted_handler_emails.pop(0)
                handler_details.save()

            final_cc_list += submitted_handler_emails
            final_cc_list += send_to_people_emails

            send_signed_spf_request(handling_request=self.handling_request,
                                    author=request_person,
                                    addresses_cc=final_cc_list,
                                    )

        return super().form_valid(form)


class SignedSpfUploadView(PassRequestMixin, FormView):
    template_name = 'gh_signed_spf_upload.html'
    form_class = SignedSpfUploadForm

    handling_request = None
    signed_spf_exists = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, uuid=self.kwargs['uuid'])
        self.signed_spf_exists = self.handling_request.documents.filter(type_id=3).exists()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'handling_request': self.handling_request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        metacontext = {}

        if self.signed_spf_exists and not context['form'].is_bound:
            context['form'] = None
            metacontext['alerts'] = [
                {
                    'text': 'SPF Document Submitted',
                    'class': 'alert-success',
                    'icon': 'check',
                    'position': 'top',
                }
            ]

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if self.signed_spf_exists:
            form.add_error(None, 'SPF Document already submitted')
            for field in form.fields:
                form.fields[field].disabled = True
            return super().form_invalid(form)

        if 'tail_number' in form.changed_data:
            self.handling_request.tail_number = form.cleaned_data['tail_number']
            self.handling_request.confirm_tail_number_action = True
            self.handling_request.save()

        spf_file = form.cleaned_data['spf_file']
        submitted_by = form.cleaned_data['submitted_by']
        sfr_document = self.handling_request.documents.create(
            type_id=3,
            description=f'Signed SPF File (submitted by {submitted_by})',
            is_staff_added=True,
        )
        sfr_document.files.create(
            file=spf_file,
            is_recent=True,
        )
        self.handling_request.activity_log.create(
            author_text=f'{self.handling_request.handling_agent.full_repr}',
            record_slug='sfr_signed_spf_upload',
            details=f'Signed SPF Document has been uploaded by {submitted_by}',
        )

        notification_staff_signed_spf_uploaded(handling_request=self.handling_request)

        return super().form_valid(form)
