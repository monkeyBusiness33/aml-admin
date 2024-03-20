from django.urls import path

from handling.views.base import HandlingServiceSelect2View
from handling.views.data_export import HandlingRequestDataExportView
from handling.views.dla_services import DlaServicesListAjaxView, DlaServicesListView, DlaServiceCreateView, \
    DlaServiceEditView, DlaServiceDeleteView
from handling.views.handling_services import HandlingServiceEditView, HandlingServicesListView, \
    HandlingServicesListAjaxView, HandlingServiceDeleteView, HandlingServiceAvailabilityAjaxView, \
    HandlingServiceTagsView, HandlingServiceDetailsView, HandlingServiceCreateView, \
    HandlingServiceAvailabilityUpdateView, HandlingServiceOrganisationsAjaxView
from handling.views.sfr_details import HandlingRequestsDetailsView, HandlingRequestAutoSPFPDFView, \
    HandlingRequestDetailsPDFView, HandlingRequestCachePurgeView
from handling.views.sfr_details_update import HandlingRequestUpdateTailNumberView, \
    HandlingRequestUpdateAircraftTypeView, HandlingRequestUpdateAssignedPersonView, HandlingRequestPayloadUpdateView, \
    HandlingRequestAirCardDetailsView, HandlingRequestUpdateApacsNumberView, HandlingRequestUpdateApacsUrlView, \
    HandlingRequestCancelView, HandlingRequestUnableToSupportView, HandlingRequestAssignedTeamMemberUpdateView, \
    HandlingRequestMissionNumberUpdateView, HandlingRequestCallsignUpdateView, HandlingRequestConfirmCallsignView, \
    HandlingRequestTypeUpdateView, HandlingRequestConversationCreateView, HandlingRequestUpdateRecurrenceView, \
    HandlingRequestCancelRecurrenceView, HandlingRequestParkingConfirmationView, HandlingRequestAogView, \
    HandlingRequestAircraftServiceableView, HandlingRequestConfirmTailNumberView, HandlingRequestAdminEditingView
from handling.views.sfr_documents import HandlingRequestDocumentsListAjaxView, HandlingRequestDocumentCreateView, \
    HandlingRequestDocumentUpdateView, HandlingRequestDocumentHistoryView, HandlingDocumentDoDShowHideView
from handling.views.sfr_fuel_booking import HandlingRequestFuelBookingStaffUpdateView, \
    HandlingRequestFuelReleaseUploadView, HandlingRequestFuelReleaseRemoveView, \
    HandlingRequestFuelBookingConfirmationView
from handling.views.sfr_ground_handling import HandlingRequestUpdateHandlerView, SendHandlingRequestView, \
    HandlingRequestGroundHandlingConfirmationView, HandlingRequestGroundHandlingCancellationView
from handling.views.sfr_movement import HandlingRequestUpdatePPRView, HandlingServiceUpdateMovementDetailsView
from handling.views.sfr_ops_checklist import HandlingRequestOpsChecklistAjaxView, \
    SfrOpsChecklistSettingsLocationsListAjaxView, SfrOpsChecklistSettingsListAjaxView, SfrOpsChecklistSettingsView, \
    SfrOpsChecklistSettingsItemCreateView, SfrOpsChecklistSettingsItemEditView, SfrOpsChecklistSettingsItemDeleteView, \
    HandlingRequestOpsChecklistItemCreateView, HandlingRequestOpsChecklistItemCompleteView
from handling.views.sfr_services import HandlingRequestAddServiceView, HandlingRequestsConfirmView, \
    HandlingServiceInternalNoteView, HandlingRequestDeleteServiceView
from handling.views.sfr_create_update import HandlingRequestCreateView, HandlingRequestCopyView, \
    HandlingRequestUpdateView, HandlingRequestReinstateView, HandlingRequestAircraftCreateView
from handling.views.sfr_lists import HandlingRequestsListAjaxView, HandlingRequestsListView, \
    HandlingRequestsListCalendarJsonResponse, HandlingRequestsListCalendarView
from handling.views.spf_v2 import HandlingRequestSpfV2ServicesAjaxView, HandlingRequestSpfV2ServiceUpdateView, \
    HandlingRequestSpfV2ReconciledView, SpfToReconcileAjaxView, SpfToReconcileView, SpfToReconcileModalView, \
    RequestSignedSpfView, SignedSpfUploadView

urlpatterns = [
    path('handling/services_ajax/', HandlingServicesListAjaxView.as_view(), name='handling_services_ajax'),
    path('handling/services/', HandlingServicesListView.as_view(), name='handling_services'),
    path('handling/services/select/', HandlingServiceSelect2View.as_view(), name='handling_services_select2'),

    path('handling/service/edit/<int:pk>/', HandlingServiceEditView.as_view(), name='handling_service_edit'),
    path('handling/service/delete/<int:pk>/', HandlingServiceDeleteView.as_view(), name='handling_service_delete'),

    path('handling/service/<int:pk>/availability_ajax/', HandlingServiceAvailabilityAjaxView.as_view(),
         name='handling_service_availability_ajax'),

    path('handling/service/<int:pk>/tags/', HandlingServiceTagsView.as_view(), name='handling_service_tags'),
    path('handling/service/<int:pk>/', HandlingServiceDetailsView.as_view(), name='handling_service'),
    path('handling/services/add/', HandlingServiceCreateView.as_view(), name='handling_services_add'),
    path('handling/services/<int:service>/availability/<slug:action>/<int:airport>/',
         HandlingServiceAvailabilityUpdateView.as_view(), name='handling_service_availability'),

    path('handling/service/<int:handling_service_id>/organisations/', HandlingServiceOrganisationsAjaxView.as_view(),
         name='handling_service_organisations'),

    # DLA Services
    path('handling/dla_services_ajax/', DlaServicesListAjaxView.as_view(), name='handling_dla_services_ajax'),
    path('handling/dla_services/', DlaServicesListView.as_view(), name='handling_dla_services'),
    path('handling/dla_services/create/', DlaServiceCreateView.as_view(), name='handling_dla_services_create'),
    path('handling/dla_services/<int:pk>/edit/', DlaServiceEditView.as_view(), name='handling_dla_services_edit'),
    path('handling/dla_services/<int:pk>/delete/', DlaServiceDeleteView.as_view(), name='handling_dla_services_delete'),

    # S&F Requests List
    path('handling/requests_ajax/', HandlingRequestsListAjaxView.as_view(), name='handling_requests_ajax'),
    path('handling/requests/', HandlingRequestsListView.as_view(), name='handling_requests'),

    # S&F Requests Calendar
    path('handling/requests_calendar_json/', HandlingRequestsListCalendarJsonResponse.as_view(),
         name='handling_requests_calendar_json'),
    path('handling/requests_calendar/', HandlingRequestsListCalendarView.as_view(), name='handling_requests_calendar'),

    # Data Export
    path('handling/requests/export/', HandlingRequestDataExportView.as_view(), name='missions_export'),

    path('handling/requests/create/', HandlingRequestCreateView.as_view(), name='handling_request_create'),
    path('handling/requests/copy/<int:pk>/', HandlingRequestCopyView.as_view(), name='handling_request_copy'),
    path('handling/requests/update/<int:pk>/', HandlingRequestUpdateView.as_view(), name='handling_request_update'),
    path('handling/requests/add_service/<int:pk>/', HandlingRequestAddServiceView.as_view(),
         name='handling_request_add_service'),
    path('handling/requests/update_tail_number/<int:pk>/', HandlingRequestUpdateTailNumberView.as_view(),
         name='handling_request_update_tail_number'),
    path('handling/requests/confirm_tail_number/<int:pk>/', HandlingRequestConfirmTailNumberView.as_view(),
         name='handling_request_confirm_tail_number'),
    path('handling/requests/<int:pk>/update_aircraft_type/', HandlingRequestUpdateAircraftTypeView.as_view(),
         name='handling_request_update_aircraft_type'),

    path('handling/create_aircraft/<int:operator_id>/', HandlingRequestAircraftCreateView.as_view(),
         name='handling_request_create_aircraft'),

    path('handling/requests/<int:pk>/', HandlingRequestsDetailsView.as_view(), name='handling_request'),
    path('handling/requests/<int:pk>/reinstate_mission/', HandlingRequestReinstateView.as_view(),
         name='handling_request_reinstate'),

    path('handling/requests/<int:pk>/set_handler/', HandlingRequestUpdateHandlerView.as_view(),
         name='handling_request_set_handler'),
    path('handling/requests/<int:pk>/send_handling_request/', SendHandlingRequestView.as_view(),
         name='send_handling_request'),
    path('handling/requests/<int:pk>/ground_handling_confirmation/',
         HandlingRequestGroundHandlingConfirmationView.as_view(),
         name='handling_request_ground_handling_confirmation'),

    path('handling/requests/<int:pk>/ground_handling_cancellation/',
         HandlingRequestGroundHandlingCancellationView.as_view(),
         name='handling_request_ground_handling_cancellation'),

    path('handling/requests/<int:pk>/change_person/', HandlingRequestUpdateAssignedPersonView.as_view(),
         name='handling_request_change_person'),
    path('handling/requests/<int:pk>/update_payload/', HandlingRequestPayloadUpdateView.as_view(),
         name='handling_request_payload'),
    path('handling/requests/<int:pk>/air_card_details/', HandlingRequestAirCardDetailsView.as_view(),
         name='handling_request_air_card_details'),
    path('handling/requests/<int:handling_request_id>/fuel_booking_staff_update/',
         HandlingRequestFuelBookingStaffUpdateView.as_view(), name='handling_request_fuel_booking_staff_update'),
    path('handling/requests/fuel_release/<int:pk>/upload/', HandlingRequestFuelReleaseUploadView.as_view(),
         name='handling_request_upload_fuel_release'),
    path('handling/requests/fuel_release/<int:pk>/remove/', HandlingRequestFuelReleaseRemoveView.as_view(),
         name='handling_request_remove_fuel_release'),
    path('handling/requests/<int:pk>/update_ppr/', HandlingRequestUpdatePPRView.as_view(),
         name='handling_request_update_ppr'),
    path('handling/requests/<int:pk>/update_apacs_number/', HandlingRequestUpdateApacsNumberView.as_view(),
         name='handling_request_update_apacs_number'),
    path('handling/requests/<int:pk>/update_apacs_url/', HandlingRequestUpdateApacsUrlView.as_view(),
         name='handling_request_update_apacs_url'),
    path('handling/requests/<int:pk>/cancel/', HandlingRequestCancelView.as_view(), name='handling_request_cancel'),
    path('handling/requests/<int:pk>/unable_to_support/', HandlingRequestUnableToSupportView.as_view(),
         name='handling_request_unable_to_support'),
    path('handling/requests/<int:pk>/set_aog/', HandlingRequestAogView.as_view(),
         name='handling_request_set_aog'),
    path('handling/requests/movement/<int:pk>/aircraft_serviceable/', HandlingRequestAircraftServiceableView.as_view(),
         name='handling_request_aircraft_serviceable'),
    path('handling/requests/<int:pk>/assigned_team_member/', HandlingRequestAssignedTeamMemberUpdateView.as_view(),
         name='handling_request_assigned_team_member'),
    path('handling/requests/<int:pk>/update_mission_number/', HandlingRequestMissionNumberUpdateView.as_view(),
         name='handling_request_update_mission_number'),
    path('handling/requests/<int:pk>/update_mission_callsign/', HandlingRequestCallsignUpdateView.as_view(),
         name='handling_request_update_mission_callsign'),
    path('handling/requests/<int:pk>/confirm_mission_callsign/', HandlingRequestConfirmCallsignView.as_view(),
         name='handling_request_confirm_mission_callsign'),
    path('handling/requests/<int:pk>/update_mission_type/', HandlingRequestTypeUpdateView.as_view(),
         name='handling_request_update_mission_type'),
    path('handling/requests/<int:pk>/get_as_pdf/', HandlingRequestDetailsPDFView.as_view(),
         name='handling_request_get_as_pdf'),
    path('handling/requests/<int:pk>/get_auto_spf/', HandlingRequestAutoSPFPDFView.as_view(),
         name='handling_request_get_auto_spf'),
    path('handling/requests/<int:pk>/parking_confirmation/', HandlingRequestParkingConfirmationView.as_view(),
         name='handling_request_confirm_parking'),
    path('handling/requests/<int:pk>/spf_v2_services/', HandlingRequestSpfV2ServicesAjaxView.as_view(),
         name='handling_request_spf_v2_services'),
    path('handling/requests/spf_v2_services/<int:pk>/update/', HandlingRequestSpfV2ServiceUpdateView.as_view(),
         name='handling_request_spf_v2_service_update'),
    path('handling/requests/<int:pk>/spf_v2_reconciled/', HandlingRequestSpfV2ReconciledView.as_view(),
         name='handling_request_spf_v2_reconciled'),
    path('handling/requests/<int:pk>/admin_editing/', HandlingRequestAdminEditingView.as_view(),
         name='handling_request_admin_editing'),
    path('handling/requests/<int:pk>/request_signed_spf/', RequestSignedSpfView.as_view(),
         name='handling_request_request_signed_spf'),
    path('upload_signed_spf/<str:uuid>/', SignedSpfUploadView.as_view(),
         name='handling_request_upload_signed_spf'),

    path('handling/requests/<int:handling_request_id>/conversation_create/',
         HandlingRequestConversationCreateView.as_view(),
         name='handling_request_chat_create'),

    path('handling/requests/<int:pk>/fuel_booking_confirmation/', HandlingRequestFuelBookingConfirmationView.as_view(),
         name='fuel_booking_confirmation'),

    path('handling/requests/confirm/<slug:scope>/<int:pk>/',
         HandlingRequestsConfirmView.as_view(), name='handling_request_confirm'),
    path('handling/requests/service/<int:pk>/internal_note/',
         HandlingServiceInternalNoteView.as_view(), name='handling_request_service_int_note'),
    path('handling/requests/remove_requested_service/<int:pk>/',
         HandlingRequestDeleteServiceView.as_view(), name='handling_request_remove_service'),

    path('handling/requests/update_movement/<int:pk>/',
         HandlingServiceUpdateMovementDetailsView.as_view(),
         name='handling_request_update_movement'),

    path('handling/requests/update_recurrence/<int:pk>/',
         HandlingRequestUpdateRecurrenceView.as_view(),
         name='handling_request_update_recurrence'),

    path('handling/requests/cancel_recurrence/<int:pk>/',
         HandlingRequestCancelRecurrenceView.as_view(),
         name='handling_request_cancel_recurrence'),

    path('handling/requests/<int:pk>/purge_cache/', HandlingRequestCachePurgeView.as_view(),
         name='handling_request_purge_cache'),

    # SPF To Reconcile
    path('handling/spf_to_reconcile_ajax/', SpfToReconcileAjaxView.as_view(), name='handling_spf_to_reconcile_ajax'),
    path('handling/spf_to_reconcile/', SpfToReconcileView.as_view(), name='handling_spf_to_reconcile'),
    path('handling/spf_reconcile/<int:pk>/', SpfToReconcileModalView.as_view(), name='handling_spf_reconcile'),

    # S&F Request Documents
    path('handling/requests/<int:pk>/documents_ajax/',
         HandlingRequestDocumentsListAjaxView.as_view(), name='handling_request_documents_ajax'),
    path('handling/requests/<int:handling_request_id>/create_document/',
         HandlingRequestDocumentCreateView.as_view(), name='handling_request_documents_create'),
    path('handling/requests/update_document/<int:pk>/',
         HandlingRequestDocumentUpdateView.as_view(), name='handling_request_document_update'),
    path('handling/requests/document_history/<int:pk>/',
         HandlingRequestDocumentHistoryView.as_view(), name='handling_request_document_history'),

    path('handling/requests/documents/<int:pk>/show/',
         HandlingDocumentDoDShowHideView.as_view(), name='handling_document_show_hide'),

    # S&F Request Ops Checklist
    path('handling/ops_checklist_settings/', SfrOpsChecklistSettingsView.as_view(), name='sfr_ops_checklist_settings'),
    path('handling/ops_checklist_settings_ajax/',
         SfrOpsChecklistSettingsListAjaxView.as_view(), name='sfr_ops_checklist_settings_ajax'),
    path('handling/ops_checklist_settings_location_specific_ajax/',
         SfrOpsChecklistSettingsLocationsListAjaxView.as_view(),
         name='sfr_ops_checklist_settings_location_specific_ajax'),

    path('handling/ops_checklist_settings/item/create',
         SfrOpsChecklistSettingsItemCreateView.as_view(), name='sfr_ops_checklist_settings_create_item'),
    path('handling/ops_checklist_settings/item/<int:pk>/update',
         SfrOpsChecklistSettingsItemEditView.as_view(), name='sfr_ops_checklist_settings_update_item'),
    path('handling/ops_checklist_settings/item/<int:pk>/delete',
         SfrOpsChecklistSettingsItemDeleteView.as_view(), name='sfr_ops_checklist_settings_delete_item'),

    path('handling/request/<int:request_pk>/ops_checklist_ajax/', HandlingRequestOpsChecklistAjaxView.as_view(),
         name='handling_request_ops_checklist'),
    path('handling/request/<int:request_pk>/ops_checklist/item/create',
         HandlingRequestOpsChecklistItemCreateView.as_view(),
         name='handling_request_ops_checklist_create_item'),
    path('handling/request/<int:request_pk>/ops_checklist/item/<int:pk>/complete',
         HandlingRequestOpsChecklistItemCompleteView.as_view(),
         name='handling_request_ops_checklist_complete_item'),
]
