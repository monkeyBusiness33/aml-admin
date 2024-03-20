from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse_lazy

from handling.forms.sfr_auto_spf import HandlingRequestAutoSpfSend
from handling.forms.sfr_handler import HandlingRequestUpdateHandlerForm, \
    HandlingRequestGroundHandlingCancellationForm, HandlingRequestGroundHandlingConfirmationForm
from handling.models import HandlingRequest
from handling.utils.sfr_ground_handling_confirmation import sfr_confirm_ground_handling
from user.mixins import AdminPermissionsMixin


class HandlingRequestUpdateHandlerView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'handling_request/_modal_update_handler.html'
    model = HandlingRequest
    form_class = HandlingRequestUpdateHandlerForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Select Ground Handler',
            'icon': 'fa-sticky-note',
            'text': f'Please select the ground handler for this request. If the desired ground handler does not '
                    f'appear in the list, you can create it by entering the name.',
            'form_id': 'handling_request_handler_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Select',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        request_person = getattr(self.request.user, 'person')
        form.instance.updated_by = request_person
        form.instance.supress_gh_cancellation_email = form.cleaned_data['mark_as_sent_manually']
        return super().form_valid(form)


class SendHandlingRequestView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = HandlingRequestAutoSpfSend
    permission_required = ['handling.p_update']

    handling_request = None
    handler_email_addresses = []
    departure_update_only = False

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])
        self.handler_email_addresses = self.handling_request.handling_agent.get_email_address()

        if getattr(self.handling_request, 'opened_gh_amendment_session', False):
            self.departure_update_only = self.handling_request.opened_gh_amendment_session.\
                is_departure_update_after_arrival

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
                                    ' address that the ground handling request should be sent to (this will be' \
                                    ' stored for future use)'.format(
                                        handler=self.handling_request.handling_agent.trading_or_registered_name)

        ground_handler = getattr(self.handling_request.handling_agent, 'full_repr')

        metacontext = {
            'title': 'Send Departure Update to GH' if self.departure_update_only else 'Send Handling Request',
            'icon': 'fa-sticky-note',
            'text': f'Do you wish to send an auto-generated handling request and SPF form to the '
                    f'<b>"{ ground_handler }"</b> ground handler?',
            'text_danger': handler_no_email_text,
            'multi_button': True,
            'action_button1_text': 'Request Already Sent Externally',
            'action_button1_class': 'btn-gray-200',
            'action_button2_text': 'Send',
            'action_button2_class': 'btn-success',
            'cancel_button_class': 'btn-gray-200',
            'form_id': 'send_handling_request_to_handler',
            'js_scripts': [
                static('js/sfr_send_to_handler.js'),
            ],
        }

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

            # 'send_request_via_email' boolean value
            send_request_via_email = form.cleaned_data['multi_button']

            # Send AutoSPF to Handler
            final_cc_list += submitted_handler_emails
            final_cc_list += send_to_people_emails

            self.handling_request = sfr_confirm_ground_handling(
                handling_request=self.handling_request,
                author=request_person,
                sent_externally=not send_request_via_email,
                email_cc_list=final_cc_list,
                departure_update_only=self.departure_update_only,
            )

            self.handling_request.updated_by = request_person
            self.handling_request.save()

        return super().form_valid(form)


class HandlingRequestGroundHandlingCancellationView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = HandlingRequestGroundHandlingCancellationForm
    permission_required = ['handling.p_update']

    handling_request = None
    ground_handler = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Ground Handling Cancellation',
            'icon': 'fa-ban',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Send Cancellation',
            'cancel_button_class': 'btn-gray-200',
        }
        if hasattr(self.handling_request, 'auto_spf'):
            metacontext['text'] = ('Do you wish to send cancellation request to the'
                                   ' <b>"{ground_handler}"</b> ground handler?').format(
                ground_handler=self.handling_request.auto_spf.sent_to.full_repr,
            )
        else:
            metacontext['text_danger'] = 'Ground Handling already cancelled for this S&F Request'
            metacontext['hide_action_button'] = True
            context['form'] = None

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.handling_request.updated_by = getattr(self, 'person')
        self.handling_request.supress_gh_cancellation_email = form.cleaned_data['mark_as_sent_manually']
        self.handling_request.cancel_ground_handling = True
        if not is_ajax(self.request.META):
            self.handling_request.save()
        return super().form_valid(form)


class HandlingRequestGroundHandlingConfirmationView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = HandlingRequestGroundHandlingConfirmationForm
    permission_required = ['handling.p_update']
    handling_request = None
    departure_update_only = False

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['pk'])
        self.departure_update_only = self.handling_request.is_awaiting_departure_update_confirmation

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        footer_buttons_left = [
            {'title': 'Resend Handling Request',
             'url': reverse_lazy('admin:send_handling_request', kwargs={'pk': self.handling_request.pk}),
             }
        ]

        metacontext = {
            'title': 'Departure Update Confirmed' if self.departure_update_only else f'Ground Handling Confirmed',
            'icon': 'fa-sticky-note',
            'text': 'Do you wish to update the ground handling status to confirmed?',
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm',
            'cancel_button_class': 'btn-gray-200',
            'footer_buttons_left': footer_buttons_left,
            'handling_request': self.handling_request,
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.handling_request.updated_by = getattr(self, 'person')
        self.handling_request.is_handling_confirmed = True
        self.handling_request.confirm_handling_services = True
        self.handling_request.is_awaiting_departure_update_confirmation = False
        if not is_ajax(self.request.META):
            self.handling_request.save()
        return super().form_valid(form)
