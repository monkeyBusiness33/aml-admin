from bootstrap_modal_forms.generic import BSModalUpdateView
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView

from mission.forms.details_update import MissionAssignedTeamMemberUpdateForm
from mission.models import Mission, MissionLeg
from mission.views_shared.communications import MissionConversationCreateMixin
from mission.views_shared.details_update import MissionCallsignUpdateMixin, MissionCallsignConfirmationMixin, \
    MissionNumberUpdateMixin, MissionTailNumberUpdateMixin, MissionTypeUpdateMixin, MissionAircraftTypeUpdateMixin, \
    MissionApacsNumberUpdateMixin, MissionApacsUrlUpdateMixin, MissionAirCardDetailsMixin, MissionConfirmationMixin, \
    MissionCancellationMixin
from mission.views_shared.fueling_requirements_views import MissionFuelingRequirementsMixin
from mission.views_shared.mission_amend_timings import MissionAmendTimingsMixin
from mission.views_shared.mission_cargo import MissionCargoUpdateMixin
from mission.views_shared.mission_crew import MissionCrewUpdateMixin
from mission.views_shared.mission_documents import MissionDocumentsListAjaxMixin, MissionDocumentCreateMixin, \
    MissionDocumentUpdateMixin, MissionDocumentHistoryMixin
from mission.views_shared.mission_ground_servicing import MissionGroundServicingUpdateMixin
from mission.views_shared.mission_leg_update import MissionLegQuickEditMixin, MissionLegChangeAircraftMixin, \
    MissionLegCancelMixin
from mission.views_shared.mission_packet_pdf import MissionPacketPdfMixin
from mission.views_shared.mission_passengers import MissionPassengersMixin
from user.mixins import AdminPermissionsMixin


class MissionDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'mission_details/00_mission.html'
    model = Mission
    context_object_name = 'mission'
    permission_required = ['handling.p_view']

    def get_queryset(self):
        queryset = Mission.objects.include_details().select_related(
            'requesting_person__details',
            'assigned_mil_team_member__details',
            'organisation'
        ).prefetch_related(
            'aircraft',
        )
        return queryset


class MissionAssignedTeamMemberUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = Mission
    form_class = MissionAssignedTeamMemberUpdateForm
    permission_required = ['handling.p_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        metacontext = {
            'title': f'Update Assigned Military Team Member',
            'icon': 'fa-user',
            'action_button_class': 'btn-success',
            'action_button_text': 'Update',
            'cancel_button_class': 'btn-gray-200',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        form.instance.updated_by = getattr(self, 'person')
        return super().form_valid(form)


class MissionCallsignUpdateView(AdminPermissionsMixin, MissionCallsignUpdateMixin):
    permission_required = ['core.ops_handling_update_callsign']


class MissionCallsignConfirmationView(AdminPermissionsMixin, MissionCallsignConfirmationMixin):
    permission_required = ['core.ops_handling_update_callsign']


class MissionNumberUpdateView(AdminPermissionsMixin, MissionNumberUpdateMixin):
    permission_required = ['handling.p_update']


class MissionTailNumberUpdateView(AdminPermissionsMixin, MissionTailNumberUpdateMixin):
    permission_required = ['handling.p_update']


class MissionTypeUpdateView(AdminPermissionsMixin, MissionTypeUpdateMixin):
    permission_required = ['handling.p_update']


class MissionAircraftTypeUpdateView(AdminPermissionsMixin, MissionAircraftTypeUpdateMixin):
    permission_required = ['handling.p_update']


class MissionApacsNumberUpdateView(AdminPermissionsMixin, MissionApacsNumberUpdateMixin):
    permission_required = ['handling.p_update']


class MissionApacsUrlUpdateView(AdminPermissionsMixin, MissionApacsUrlUpdateMixin):
    permission_required = ['handling.p_update']


class MissionAirCardDetailsView(AdminPermissionsMixin, MissionAirCardDetailsMixin):
    permission_required = ['handling.p_update']


class MissionConfirmationView(AdminPermissionsMixin, MissionConfirmationMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionFuelingRequirementsView(AdminPermissionsMixin, MissionFuelingRequirementsMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionDocumentsListAjaxView(AdminPermissionsMixin, MissionDocumentsListAjaxMixin):
    permission_required = ['handling.p_view']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionDocumentCreateView(AdminPermissionsMixin, MissionDocumentCreateMixin):
    permission_required = ['handling.p_create']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionDocumentUpdateView(AdminPermissionsMixin, MissionDocumentUpdateMixin):
    permission_required = ['handling.p_update']


class MissionDocumentHistoryView(AdminPermissionsMixin, MissionDocumentHistoryMixin):
    permission_required = ['handling.p_view']


class MissionCancellationView(AdminPermissionsMixin, MissionCancellationMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionConversationCreateView(AdminPermissionsMixin, MissionConversationCreateMixin):
    permission_required = ['handling.p_dod_comms']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionAmendTimingsView(AdminPermissionsMixin, MissionAmendTimingsMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionPacketPdfView(AdminPermissionsMixin, MissionPacketPdfMixin):
    permission_required = ['handling.p_view']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission = get_object_or_404(Mission, pk=self.kwargs['pk'])


class MissionCrewUpdateView(AdminPermissionsMixin, MissionCrewUpdateMixin):
    permission_required = ['handling.p_update']


class MissionPassengersView(AdminPermissionsMixin, MissionPassengersMixin):
    permission_required = ['handling.p_update']


class MissionCargoUpdateView(AdminPermissionsMixin, MissionCargoUpdateMixin):
    permission_required = ['handling.p_update']


class MissionGroundServicingUpdateView(AdminPermissionsMixin, MissionGroundServicingUpdateMixin):
    permission_required = ['handling.p_update']


class MissionLegQuickEditView(AdminPermissionsMixin, MissionLegQuickEditMixin):
    permission_required = ['handling.p_update']


class MissionLegChangeAircraftView(AdminPermissionsMixin, MissionLegChangeAircraftMixin):
    permission_required = ['handling.p_update']


class MissionLegCancelView(AdminPermissionsMixin, MissionLegCancelMixin):
    permission_required = ['handling.p_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.mission_leg = get_object_or_404(MissionLeg, pk=self.kwargs['pk'])
