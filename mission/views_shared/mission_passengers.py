from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404

from mission.forms.mission_passengers import MissionLegPassengersPayloadForm, MissionLegPassengersPayloadBaseFormSet
from mission.models import Mission, MissionLegPassengersPayload


class MissionPassengersMixin(BSModalFormView):
    template_name = 'mission_details/_modal_mission_passengers.html'
    model = MissionLegPassengersPayload

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

    def get_form_class(self):
        pax_count = self.mission.passengers_max or 0

        passengers_payload_formset = modelformset_factory(
            MissionLegPassengersPayload,
            min_num=pax_count,
            extra=pax_count + 10,
            can_delete=False,
            form=MissionLegPassengersPayloadForm,
            formset=MissionLegPassengersPayloadBaseFormSet,
            fields=[
                'identifier',
                'gender',
                'weight',
                'note',
                'mission_legs',
            ]
        )
        return passengers_payload_formset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Manage Passengers',
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
                record_slug='mission_passengers_update',
                details='Mission Passengers has been updated',
            )

            for mission_leg in self.mission.active_legs:
                mission_leg.pob_pax = mission_leg.passengers.count()
                mission_leg.prevent_mission_update = True
                mission_leg.updated_by = getattr(self, 'person')
                mission_leg.save()
            self.mission.updated_by = getattr(self, 'person')
            self.mission.save()

        return super().form_valid(form)
