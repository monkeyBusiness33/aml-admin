from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.shortcuts import get_object_or_404

from mission.forms.mission_crew import MissionCrewFormSet
from mission.models import MissionCrewPosition, Mission


class MissionCrewUpdateMixin(BSModalFormView):
    template_name = 'mission_details/_modal_mission_crew.html'
    model = MissionCrewPosition
    form_class = MissionCrewFormSet
    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mission': self.mission})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Manage Mission Crew',
            'icon': 'fa-users',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        context['mission'] = self.mission
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.save()
            self.mission.activity_log.create(
                author=getattr(self, 'person'),
                record_slug='mission_crew_update',
                details='Mission Crew has been updated',
            )
            self.mission.updated_by = getattr(self, 'person')
            self.mission.save()
        return super().form_valid(form)
