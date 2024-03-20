from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.db.models import F, Sum
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404

from mission.forms.mission_cargo import MissionLegCargoPayloadBaseFormSet, MissionLegCargoPayloadForm
from mission.models import Mission, MissionLegCargoPayload


class MissionCargoUpdateMixin(BSModalFormView):
    template_name = 'mission_details/_modal_mission_cargo.html'
    model = MissionLegCargoPayload

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
        passengers_payload_formset = modelformset_factory(
            MissionLegCargoPayload,
            extra=30,
            can_delete=True,
            form=MissionLegCargoPayloadForm,
            formset=MissionLegCargoPayloadBaseFormSet,
            fields=[
                'description',
                'length',
                'width',
                'height',
                'weight',
                'quantity',
                'is_dg',
                'note',
                'mission_legs',
            ]
        )
        return passengers_payload_formset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Manage Cargo',
            'icon': 'fa-cart-flatbed-suitcase',
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
                record_slug='mission_cargo_update',
                details='Mission Cargo has been updated',
            )

            # Update MissionLeg Cargo Weight
            for mission_leg in self.mission.active_legs:
                mission_leg_cargo = mission_leg.cargo.annotate(
                    row_weight=F('weight') * F('quantity')
                ).aggregate(total_weight=Sum('row_weight'))

                mission_leg.cob_lbs = mission_leg_cargo['total_weight']
                mission_leg.prevent_mission_update = True
                mission_leg.updated_by = getattr(self, 'person')
                mission_leg.save()
            self.mission.updated_by = getattr(self, 'person')
            self.mission.save()

        return super().form_valid(form)
