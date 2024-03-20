from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.html import format_html, format_html_join

from core.forms import NumberedMultiButtonFormConfirmationForm
from handling.models import HandlingRequest
from handling.utils.handling_request_func import handling_request_cancel_actions
from handling.utils.handling_request_utils import sfr_get_cancellation_terms


class HandlingRequestCancelMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = HandlingRequest
    form_class = NumberedMultiButtonFormConfirmationForm

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Cancel S&F Request',
            'icon': 'fa-ban',
            'text': f'Please confirm that you want to cancel this Servicing & Fueling Request',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Cancel',
            'cancel_button_class': 'btn-gray-200',
        }

        app_mode = getattr(self.request, 'app_mode')
        cancellation_grace_period = app_mode == 'ops_portal' and self.handling_request.is_cancelable_grace_period

        if not self.handling_request.is_cancelable and not cancellation_grace_period:
            metacontext['text'] = ''
            status = HandlingRequest.STATUS_DETAILS[self.handling_request.get_status]['detail']

            if self.handling_request.cancelled:
                metacontext['text_danger'] = 'S&F Request already cancelled, please refresh the page.'
            elif app_mode == 'ops_portal' and self.handling_request.get_status == 4:
                metacontext['text_danger'] = f"Completed S&F Requests can only be cancelled within a 24-hour window"\
                                             " after departure time."
            else:
                metacontext['text_danger'] = f"{status} S&F Requests cannot be cancelled after departure time."

            metacontext['hide_action_button'] = True

        if self.handling_request.recurrence_groups_membership.exists():
            recurrence_group = self.handling_request.recurrence_groups.first()
            requests_list_html = ''

            for recurrence_request in recurrence_group.handling_requests.order_by('created_at'):
                recurrence_request_url = ''
                if app_mode == 'ops_portal':
                    recurrence_request_url = reverse_lazy('admin:handling_request',
                                                          kwargs={'pk': recurrence_request.pk})
                elif app_mode == 'dod_portal':
                    recurrence_request_url = reverse_lazy('dod:request', kwargs={'pk': recurrence_request.pk})

                html = '<a href="{url}">{callsign}</a> - {arrival_date}/{departure_date} ({status})</br>'.format(
                    callsign=recurrence_request.callsign,
                    arrival_date=recurrence_request.arrival_movement.date.strftime("%Y-%m-%d"),
                    departure_date=recurrence_request.departure_movement.date.strftime("%Y-%m-%d"),
                    url=recurrence_request_url,
                    status=HandlingRequest.STATUS_DETAILS[recurrence_request.get_status]['detail'],
                    )
                requests_list_html += html

            metacontext = {
                'title': f'Cancel S&F Request',
                'icon': 'fa-ban',
                'text': f'Please confirm that you want to cancel this Servicing & Fueling Request',
                'text_danger': f'This S&F Request is a part of recurrence sequence, you can cancel this particular '
                               f'request or all requests in sequence: </br> {requests_list_html}',
                'numbered_multi_button': True,
                'action_button1_text': 'Cancel All Requests',
                'action_button1_class': 'btn-danger',
                'action_button2_text': 'Cancel Current Request',
                'action_button2_class': 'btn-warning',
                'cancel_button_class': 'btn-gray-200',
            }

            # Disable 'Cancel Current Request' button if request not cancellable / past grace period
            if not self.handling_request.is_cancelable and not cancellation_grace_period:
                metacontext.update({
                    'action_button2_class': 'btn-warning disabled',
                })

            # Disable 'Cancel All Requests' button if all of the request are not cancellable / past grace period
            recurrence_group = self.handling_request.recurrence_groups.first()
            cancellable_requests_exist = any([request.is_cancelable
                                              or app_mode == 'ops_portal' and request.is_cancelable_grace_period
                                              for request in recurrence_group.handling_requests.all()])

            if not cancellable_requests_exist:
                metacontext.update({
                    'action_button1_class': 'btn-danger disabled',
                })

        if app_mode == 'ops_portal':
            cancellation_terms = sfr_get_cancellation_terms(self.handling_request)
            if cancellation_terms:
                terms_list = format_html_join("\n",
                                              "<li>{} - {}</li>", (
                                                  (term.penalty_specific_service.name, term.get_penalty_display())
                                                  for term in cancellation_terms)
                                              )

                alert_html = format_html(
                    'For your information, the ground handler\'s cancellation policy for this notice is as follows:'
                    '<br><ul class="mt-1 mb-0">{terms_list}</ul>'.format(
                        terms_list=terms_list,
                    )

                )
                cancellation_terms_alert = {
                    'text': alert_html,
                    'class': 'alert-info',
                    'icon': 'info',
                    'position': 'bottom',
                }
                metacontext.setdefault('alerts', []).append(cancellation_terms_alert)

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        request_person = getattr(self.request.user, 'person')

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            multi_button = form.cleaned_data['multi_button']
            app_mode = getattr(self.request, 'app_mode')

            # Cancel current request only
            if multi_button == 2 or multi_button == '':
                grace_period = app_mode == 'ops_portal' and self.handling_request.is_cancelable_grace_period
                handling_request_cancel_actions(handling_request=self.handling_request, author=request_person,
                                                cancellation_grace_period=grace_period)

                messages.success(self.request, f'Servicing & Fueling Request has been cancelled')

            # Cancel all related request in recurrence sequence
            if multi_button == 1:
                recurrence_group = self.handling_request.recurrence_groups.first()
                for recurrence_request in recurrence_group.handling_requests.order_by('created_at'):
                    grace_period = app_mode == 'ops_portal' and recurrence_request.is_cancelable_grace_period
                    handling_request_cancel_actions(handling_request=recurrence_request, author=request_person,
                                                    cancellation_grace_period=grace_period)

                messages.success(self.request,
                                 f'All Servicing & Fueling Requests in the recurrence sequence has been cancelled')

        return super().form_valid(form)
