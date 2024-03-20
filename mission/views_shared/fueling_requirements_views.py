from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from mission.forms.fueling_requirements import MissionFuelRequirementsFormSet
from mission.models import MissionTurnaround


class MissionFuelingRequirementsMixin(BSModalFormView):
    template_name = 'mission_details/_modal_mission_fueling_requirements.html'
    form_class = MissionFuelRequirementsFormSet
    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mission': self.mission})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Fueling Requirements',
            'icon': 'fa-users',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        context['mission'] = self.mission
        context['turnarounds'] = MissionTurnaround.objects.filter(
            mission_leg__mission=self.mission)
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.save()
            self.mission.activity_log.create(
                author=getattr(self, 'person'),
                record_slug='mission_fuel_requirements_amendment',
                details='Mission Fuel Requirements has been amended',
            )
            self.mission.updated_by = getattr(self, 'person')
            self.mission.save()
        return super().form_valid(form)
