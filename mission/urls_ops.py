from django.urls import path

from mission.views.mission_details import MissionDetailsView, MissionCallsignUpdateView, \
    MissionCallsignConfirmationView, MissionNumberUpdateView, MissionAssignedTeamMemberUpdateView, \
    MissionTailNumberUpdateView, MissionTypeUpdateView, MissionAircraftTypeUpdateView, MissionApacsNumberUpdateView, \
    MissionApacsUrlUpdateView, MissionAirCardDetailsView, MissionCrewUpdateView, MissionGroundServicingUpdateView, \
    MissionLegQuickEditView, MissionLegChangeAircraftView, MissionLegCancelView, \
    MissionConfirmationView, MissionCancellationView, MissionFuelingRequirementsView, MissionDocumentsListAjaxView, \
    MissionDocumentCreateView, MissionDocumentUpdateView, MissionDocumentHistoryView, MissionConversationCreateView, \
    MissionAmendTimingsView, MissionPacketPdfView, MissionPassengersView, MissionCargoUpdateView
from mission.views.missions import MissionsListAjaxView, MissionsListView, MissionsCalendarView, \
    MissionsCalendarJsonResponse
from mission.views.missions_create_update import MissionCreateUpdateView

urlpatterns = [

    # Missions List
    path('missions/list_ajax/', MissionsListAjaxView.as_view(), name='missions_list_ajax'),
    path('missions/list/', MissionsListView.as_view(), name='missions_list'),
    path('missions/calendar_ajax/', MissionsCalendarJsonResponse.as_view(), name='missions_calendar_json'),
    path('missions/calendar/', MissionsCalendarView.as_view(), name='missions_calendar'),
    path('missions/create/', MissionCreateUpdateView.as_view(), name='missions_create'),

    # Mission Details
    path('missions/<int:pk>/', MissionDetailsView.as_view(), name='missions_details'),

    # Mission Details Update
    path('missions/<int:pk>/update/', MissionCreateUpdateView.as_view(), name='missions_update'),
    path('missions/<int:pk>/update_callsign/', MissionCallsignUpdateView.as_view(), name='missions_update_callsign'),
    path('missions/<int:pk>/confirm_callsign/', MissionCallsignConfirmationView.as_view(),
         name='missions_confirm_callsign'),
    path('missions/<int:pk>/update_mission_number/', MissionNumberUpdateView.as_view(),
         name='missions_update_mission_number'),
    path('missions/<int:pk>/update_assigned_mil_team_member/', MissionAssignedTeamMemberUpdateView.as_view(),
         name='missions_update_assigned_mil_team_member'),
    path('missions/<int:pk>/update_tail_number/', MissionTailNumberUpdateView.as_view(),
         name='missions_update_tail_number'),
    path('missions/<int:pk>/update_type/', MissionTypeUpdateView.as_view(),
         name='missions_update_mission_type'),
    path('missions/<int:pk>/update_aircraft_type/', MissionAircraftTypeUpdateView.as_view(),
         name='missions_update_aircraft_type'),
    path('missions/<int:pk>/update_apacs_number/', MissionApacsNumberUpdateView.as_view(),
         name='missions_update_apacs_number'),
    path('missions/<int:pk>/update_apacs_url/', MissionApacsUrlUpdateView.as_view(),
         name='missions_update_apacs_url'),
    path('missions/<int:pk>/update_aircard/', MissionAirCardDetailsView.as_view(),
         name='missions_update_aircard'),
    path('missions/<int:pk>/confirm/', MissionConfirmationView.as_view(),
         name='missions_confirm'),
    path('missions/<int:pk>/cancel/', MissionCancellationView.as_view(),
         name='missions_cancel'),
    path('missions/<int:pk>/update_crew/', MissionCrewUpdateView.as_view(),
         name='missions_update_crew'),
    path('missions/<int:pk>/passengers/', MissionPassengersView.as_view(),
         name='missions_update_passengers'),
    path('missions/<int:pk>/cargo/', MissionCargoUpdateView.as_view(),
         name='missions_update_cargo'),
    path('missions/<int:pk>/fueling_requirements/', MissionFuelingRequirementsView.as_view(),
         name='missions_fueling_requirements'),
    path('missions/<int:pk>/update_ground_servicing/', MissionGroundServicingUpdateView.as_view(),
         name='missions_update_ground_servicing'),
    path('missions/<int:pk>/conversation_create/', MissionConversationCreateView.as_view(),
         name='mission_chat_create'),
    path('missions/<int:pk>/amend_timings/', MissionAmendTimingsView.as_view(),
         name='mission_amend_timings'),
    path('missions/<int:pk>/mission_packet_pdf/', MissionPacketPdfView.as_view(),
         name='mission_packet_pdf'),

    # Mission relatives
    path('missions/<int:pk>/documents_ajax/', MissionDocumentsListAjaxView.as_view(),
         name='missions_documents_ajax'),
    path('missions/<int:pk>/documents/create/', MissionDocumentCreateView.as_view(),
         name='missions_documents_create'),
    path('missions/documents/<int:pk>/update/', MissionDocumentUpdateView.as_view(),
         name='missions_documents_update'),
    path('missions/documents/<int:pk>/history/', MissionDocumentHistoryView.as_view(),
         name='missions_documents_history'),

    # Flight Legs
    path('missions/leg/<int:pk>/quick_edit/', MissionLegQuickEditView.as_view(),
         name='missions_leg_quick_edit'),
    path('missions/leg/<int:pk>/change_aircraft/', MissionLegChangeAircraftView.as_view(),
         name='missions_leg_change_aircraft'),
    path('missions/leg/<int:pk>/cancel/', MissionLegCancelView.as_view(),
         name='missions_leg_cancel'),

]
