from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404

from core.forms import ConfirmationForm
from mission.forms.details_update import MissionCallsignForm, MissionNumberForm, MissionTailNumberForm, \
    MissionTypeForm, MissionAircraftTypeForm, MissionApacsNumberForm, MissionApacsUrlForm, MissionAirCardDetailsForm
from mission.models import Mission


class MissionCallsignUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionCallsignForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Mission Callsign',
            'icon': 'fa-fighter-jet',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionCallsignConfirmationMixin(SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    success_message = 'Callsign amendment confirmed'

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        activity_log_record = self.mission.activity_log.filter(
            record_slug='mission_callsign_amendment',
            value_new=self.mission.callsign,
        ).first()

        metacontext = {
            'title': 'Confirm Callsign Amendment',
            'icon': 'fa-check',
            'text': 'This action will confirm <b>{prev_callsign} > {new_callsign}</b> callsign amendment.'.format(
                prev_callsign=activity_log_record.value_prev,
                new_callsign=activity_log_record.value_new,
            ),
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.mission.updated_by = getattr(self, 'person')
        self.mission.save()
        return super().form_valid(form)


class MissionNumberUpdateMixin(BSModalUpdateView):
    template_name = 'mission_details/_modal_mission_number.html'
    model = Mission
    form_class = MissionNumberForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        metacontext = {
            'title': f'Update Mission Number',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }
        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionTailNumberUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionTailNumberForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update Tail Number for {obj.callsign}',
            'icon': 'fa-id-card',
            'form_id': 'update_tail_number_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionTypeUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionTypeForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        metacontext = {
            'title': f'Update Mission Type',
            'icon': 'fa-edit',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }
        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionAircraftTypeUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionAircraftTypeForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        metacontext = {
            'title': f'Update Aircraft Type for {obj.callsign}',
            'icon': 'fa-fighter-jet',
            'text': f'Aircraft Type update will reset "Tail Number" value and services booking confirmation.',
            'form_id': 'update_aircraft_type_form',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionApacsNumberUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionApacsNumberForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update Diplomatic Clearance Number',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionApacsUrlUpdateMixin(BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionApacsUrlForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Update APACS URL',
            'icon': 'fa-hashtag',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionAirCardDetailsMixin(BSModalUpdateView):
    template_name = 'handling_request/_modal_aircard.html'
    model = Mission
    form_class = MissionAirCardDetailsForm

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['handling_request'] = self.get_object()

        metacontext = {
            'title': f'AIR Card Details',
            'icon': 'fa-credit-card',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionConfirmationMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = ConfirmationForm

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Confirm Drafted Mission',
            'icon': 'fa-check',
            'text': 'This action will update mission status from "Draft" to "In Progress"',
            'action_button_class': 'btn-success',
            'action_button_text': 'Confirm',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.mission.updated_by = getattr(self, 'person')
        self.mission.is_confirmed = True
        if not is_ajax(self.request.META):
            self.mission.save()
        return super().form_valid(form)


class MissionCancellationMixin(BSModalFormView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = ConfirmationForm

    mission = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Cancel Mission',
            'icon': 'fa-ban',
            'text': 'Please confirm that you want to cancel this Mission and all related S&F Requests"',
            'action_button_class': 'btn-danger',
            'action_button_text': 'Cancel Mission',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        self.mission.updated_by = getattr(self, 'person')
        self.mission.is_cancelled = True
        if not is_ajax(self.request.META):
            self.mission.save()
        return super().form_valid(form)
