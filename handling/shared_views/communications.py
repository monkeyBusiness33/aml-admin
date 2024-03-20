from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404

from chat.utils.conversations import handling_request_create_conversation
from core.forms import ConfirmationForm
from handling.models import HandlingRequest


class HandlingRequestConversationCreateMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    success_message = 'Conversation successfully created'

    handling_request = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.handling_request = get_object_or_404(HandlingRequest, pk=self.kwargs['handling_request_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Start S&F Request Conversation',
            'icon': 'fa-comments',
            'text': 'Please confirm that you want to start conversation for this S&F Request',
            'action_button_text': 'Start',
            'action_button_class': 'btn-success',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if not is_ajax(self.request.META):
            handling_request_create_conversation(handling_request=self.handling_request, author=getattr(self, 'person'))
        return response
