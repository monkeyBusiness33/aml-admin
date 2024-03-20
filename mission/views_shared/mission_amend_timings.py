from django.views.generic import TemplateView


class MissionAmendTimingsMixin(TemplateView):
    template_name = 'mission_details/_modal_amend_timings.html'
    mission = None

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Amend Mission Timings',
            'icon': 'fa-clock',
            'form_id': 'mission_amend_timings_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update Timings',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        context['mission'] = self.mission
        return context
