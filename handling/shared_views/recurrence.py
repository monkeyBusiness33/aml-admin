from bootstrap_modal_forms.generic import BSModalUpdateView
from bootstrap_modal_forms.mixins import PassRequestMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import FormView

from core.forms import ConfirmationForm
from handling.forms.sfr_recurrence import HandlingRequestRecurrenceForm
from handling.models import HandlingRequestRecurrence
from handling.utils.handling_request_func import handling_request_cancel_actions


class UpdateRecurrenceMixin(BSModalUpdateView):
    template_name = 'handling_request/_modal_update_recurrence.html'
    model = HandlingRequestRecurrence
    form_class = HandlingRequestRecurrenceForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        recurrence = self.get_object()
        requests_list_html = ''
        app_mode = getattr(self.request, 'app_mode')

        for recurrence_request in recurrence.get_future_handling_requests():
            recurrence_request_url = ''
            if app_mode == 'ops_portal':
                recurrence_request_url = reverse_lazy('admin:handling_request',
                                                      kwargs={'pk': recurrence_request.pk})
            elif app_mode == 'dod_portal':
                recurrence_request_url = reverse_lazy('dod:request', kwargs={'pk': recurrence_request.pk})

            html = '<a href="{url}">{callsign}</a> - {arrival_date}/{departure_date}</br>'.format(
                callsign=recurrence_request.callsign,
                arrival_date=recurrence_request.arrival_movement.date.strftime("%Y-%m-%d"),
                departure_date=recurrence_request.departure_movement.date.strftime("%Y-%m-%d"),
                url=recurrence_request_url,
            )
            requests_list_html += html

        metacontext = {
            'title': 'Update S&F Request Recurrence Sequence',
            'icon': 'fa-file-upload',
            'text_danger': f'Editing recurrence sequence you going to update or cancel one of next S&F Requests: '
                           f'</br> {requests_list_html}',
        }

        context['metacontext'] = metacontext
        return context


class CancelRecurrenceMixin(PassRequestMixin, FormView):
    form_class = ConfirmationForm
    recurrence = None

    def form_valid(self, form):
        for recurrence_request in self.recurrence.get_future_handling_requests():
            handling_request_cancel_actions(handling_request=recurrence_request, author=getattr(self, 'person'))
        return JsonResponse({'success': 'true'})
