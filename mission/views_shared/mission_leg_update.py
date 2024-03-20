from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.templatetags.static import static

from mission.forms.mission_leg import MissionLegQuickEditForm, MissionLegChangeAircraftForm, MissionLegCancelForm
from mission.models import MissionLeg
from mission.utils.legs_utils import mission_legs_cancel


class MissionLegQuickEditMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = MissionLeg
    form_class = MissionLegQuickEditForm

    person = None  # Should be assigned by mixin

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        mission_leg = self.get_object()
        title = 'Quick Edit Flight Leg - {sequence_id} {departure_location}>{arrival_location}'.format(
            sequence_id=mission_leg.sequence_id,
            departure_location=mission_leg.departure_location.tiny_repr,
            arrival_location=mission_leg.arrival_location.tiny_repr,
        )
        metacontext = {
            'title': title,
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
            'js_scripts': [
                static('assets/custom/bootstrap-durationpicker/bootstrap-durationpicker.js'),
                static('js/mission_leg_quick_edit.js')
            ],
            'css_files': [
                static('assets/custom/bootstrap-durationpicker/bootstrap-durationpicker.css'),
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.updated_by = self.person
        return super().form_valid(form)


class MissionLegChangeAircraftMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = MissionLeg
    form_class = MissionLegChangeAircraftForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        title = 'Change Aircraft - {sequence_id} {departure_location}>{arrival_location}'.format(
            sequence_id=self.object.sequence_id,
            departure_location=self.object.departure_location.tiny_repr,
            arrival_location=self.object.arrival_location.tiny_repr,
        )
        metacontext = {
            'title': title,
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        form.instance.propagate_aircraft_update = form.cleaned_data['apply_to_subsequent_legs']
        return super().form_valid(form)


class MissionLegCancelMixin(BSModalFormView):
    template_name = 'mission_details/_modal_mission_leg_cancel.html'
    form_class = MissionLegCancelForm

    mission_leg = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mission_leg': self.mission_leg})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        title = 'Cancel Flight Leg - {sequence_id} {departure_location}>{arrival_location}'.format(
            sequence_id=self.mission_leg.sequence_id,
            departure_location=self.mission_leg.departure_location.tiny_repr,
            arrival_location=self.mission_leg.arrival_location.tiny_repr,
        )
        metacontext = {
            'title': title,
            'icon': 'fa-trash-alt',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Cancel Flight Leg & Update Mission',
            'cancel_button_class': 'btn-gray-200',
        }

        context['mission_leg'] = self.mission_leg
        context['mission'] = self.mission_leg.mission
        context['leg_prev'] = self.mission_leg.get_prev_leg()
        context['leg_next'] = self.mission_leg.get_next_leg()
        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.mission_leg.updated_by = getattr(self, 'person')
        if not is_ajax(self.request.META):
            leg_prev = self.mission_leg.get_prev_leg()
            leg_next = self.mission_leg.get_next_leg()
            if leg_prev:
                leg_prev.updated_by = getattr(self, 'person')
                leg_prev.prevent_mission_update = True
                leg_prev.arrival_datetime = form.cleaned_data.get('prev_arrival_datetime')
                leg_prev.arrival_location = form.cleaned_data.get('new_location')
                leg_prev.save()
            if leg_next:
                leg_next.updated_by = getattr(self, 'person')
                leg_next.prevent_mission_update = True
                leg_next.departure_datetime = form.cleaned_data.get('next_departure_datetime')
                leg_next.departure_location = form.cleaned_data.get('new_location')
                leg_next.save()

            mission_legs_cancel(mission_leg=self.mission_leg)
        return super().form_valid(form)
