from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from chat.utils.conversations import mission_create_conversation
from core.forms import ConfirmationForm


class MissionConversationCreateMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    success_message = 'Conversation successfully created'

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Start Mission Conversation',
            'icon': 'fa-comments',
            'text': 'Please confirm that you want to start conversation for this Mission',
            'action_button_text': 'Start',
            'action_button_class': 'btn-success',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if not is_ajax(self.request.META):
            mission_create_conversation(mission=self.mission, author=getattr(self, 'person'))
        return response
