from django.urls import path
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from django.conf import settings

from rest_framework.routers import DefaultRouter, SimpleRouter

from chat.consumers import ChatConsumer
from dod_portal.views.base import *
from dod_portal.views.auth import *
from dod_portal.views.data_export import HandlingRequestDataExportView
from dod_portal.views.handling_requests_documents import HandlingRequestDocumentsListAjaxView, \
    HandlingRequestDocumentCreateView, HandlingRequestDocumentUpdateView, HandlingRequestDocumentHistoryView
from dod_portal.views.missions import MissionCallsignUpdateView, MissionDetailsView, MissionCreateUpdateView, \
    MissionsListView, MissionsCalendarView, MissionsCalendarJsonResponse, MissionNumberUpdateView, TailNumberUpdateView, \
    MissionAircraftTypeUpdateView, MissionApacsNumberUpdateView, MissionApacsUrlUpdateView, MissionsListAjaxView, \
    MissionCrewUpdateView, MissionLegQuickEditView, MissionLegChangeAircraftView, \
    MissionLegCancelView, MissionConfirmationView, MissionCancellationView, MissionConversationCreateView, \
    MissionAmendTimingsView, MissionDailyScheduleView, MissionCargoUpdateView, MissionPassengersUpdateView
from dod_portal.views.missions_documents import MissionDocumentsListAjaxView, MissionDocumentCreateView, \
    MissionDocumentUpdateView, MissionDocumentHistoryView, MissionPacketPdfView
from dod_portal.views.person import *
from dod_portal.views.fleet import *
from dod_portal.views.handling_requests import *

from chat.views import MessageViewSet, ConversationViewSet, MetaInformationViewSet
from handling.views.base import HandlingRequestPreferredHandlerAsyncCallback, HandlingRequestCreatePersonAsyncCallback

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()


app_name = 'dod'
urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('dod:requests')), name='index'),

    # Auth
    path('login/', DodLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # Auth URLs used as plaintext in dod/emails, care on this if uri will be changed
    path('request_password_reset/', PasswordResetView.as_view(), name='request_password_reset'),
    path('request_password_reset_complete/', PasswordResetRequestCompleteView.as_view(), name='request_password_reset_complete'),
    path('reset_password/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_set_complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Common
    path('select_organisation/', SetCurrentOrganisationView.as_view(), name='select_organisation'),
    path('select/', AuthenticatedSelect2View.as_view(), name='select2'),
    path('ping/', DummyJsonResponse.as_view(), name='ping'),
    path('tos/', PlannersPortalTermsAndConditions.as_view(), name='tos'),

    # Add Organisation Person
    path('dod/organisation/<int:organisation_id>/people/create/', OrganisationPersonCreateView.as_view(), name='organisation_people_create'),

    # Fleet
    path('dod/organisations/aircraft_operator/<int:operator_id>/fleet/create/', AircraftCreateView.as_view(), name='aircraft_operator_fleet_create'),
    path('fleet_ajax/', DodFleetAjaxView.as_view(), name='fleet_ajax'),
    path('fleet/', DodFleetListView.as_view(), name='fleet'),
    path('fleet/create/', AircraftCreateView.as_view(), name='fleet_create'),
    path('fleet/aircraft/<int:pk>/edit/', AircraftEditView.as_view(), name='fleet_edit'),
    path('fleet/aircraft/<int:pk>/remove/', AircraftDetachView.as_view(), name='fleet_remove'),

    # == HANDLING == #

    # S&F Requests List
    path('requests_ajax/', HandlingRequestsListAjaxView.as_view(), name='requests_ajax'),
    path('requests/', HandlingRequestsListView.as_view(), name='requests'),
    path('missions/export/', HandlingRequestDataExportView.as_view(), name='missions_export'),

    # S&F Requests List Calendar
    path('requests/calendar_json/',
         HandlingRequestsListCalendarJsonResponse.as_view(),
         name='handling_requests_calendar_json'),

    path('requests/calendar/',
         HandlingRequestsListCalendarView.as_view(),
         name='handling_requests_calendar'),

    path('requests/<int:pk>/', HandlingRequestsDetailsView.as_view(), name='request'),
    path('requests/<int:pk>/manage_crew/', HandlingRequestManageCrewView.as_view(), name='request_manage_crew'),
    path('requests/<int:pk>/update_tail_number/', HandlingRequestUpdateTailNumberView.as_view(), name='handling_request_update_tail_number'),
    path('requests/<int:pk>/update_aircraft_type/', HandlingRequestUpdateAircraftTypeView.as_view(), name='handling_request_update_aircraft_type'),
    path('requests/<int:pk>/update_callsign/', HandlingRequestCallsignUpdateView.as_view(), name='handling_request_update_callsign'),
    path('requests/<int:pk>/update_mission_number/', HandlingRequestMissionNumberUpdateView.as_view(), name='handling_request_update_mission_number'),
    path('requests/<int:pk>/update_apacs_number/', HandlingRequestUpdateApacsNumberView.as_view(), name='handling_request_update_apacs_number'),
    path('requests/<int:pk>/update_apacs_url/', HandlingRequestUpdateApacsUrlView.as_view(), name='handling_request_update_apacs_url'),
    path('requests/<int:pk>/cancel/', HandlingRequestCancelView.as_view(), name='handling_request_cancel'),
    path('requests/<int:pk>/get_as_pdf/', HandlingRequestDetailsPDFView.as_view(), name='handling_request_get_as_pdf'),
    path('requests/<int:pk>/reinstate/', HandlingRequestReinstateView.as_view(), name='handling_request_reinstate'),
    path('requests/<int:pk>/payload/', HandlingRequestPayloadUpdateView.as_view(), name='handling_request_payload'),
    path('requests/<int:pk>/aog/', HandlingRequestAircraftOnGroundView.as_view(), name='handling_request_set_aog'),
    path('requests/movement/<int:pk>/aircraft_serviceable/', HandlingRequestAircraftServiceableView.as_view(), name='handling_request_aircraft_serviceable'),
    path('requests/movement/<int:pk>/add_service/', HandlingRequestAddServiceView.as_view(), name='request_add_service'),
    path('requests/movement/<int:pk>/update/', HandlingRequestUpdateMovementView.as_view(), name='request_movement_update'),
    path('requests/create/', HandlingRequestCreateView.as_view(), name='request_create'),
    path('requests/create/create_aircraft/<int:operator_id>/', HandlingRequestAircraftCreateView.as_view(),
         name='handling_request_create_aircraft'),
    path('requests/copy/<int:handling_request_id>/', HandlingRequestCopyView.as_view(), name='request_copy'),
    path('requests/<int:pk>/update/', HandlingRequestUpdateView.as_view(), name='request_update'),
    path('requests/update_service_note/<int:pk>/', HandlingServiceNoteView.as_view(), name='update_service_note'),
    path('requests/created_person_callback/<int:organisation_id>/', HandlingRequestCreatePersonAsyncCallback.as_view(), name='created_person_callback'),
    path('requests/get_preferred_handler/<int:organisation_id>/<int:location_id>/',
         HandlingRequestPreferredHandlerAsyncCallback.as_view(), name='get_preferred_handler'),
    path('services/select/', HandlingServiceSelect2View.as_view(), name='handling_services_select2'),

    path('handling/requests/update_recurrence/<int:pk>/',
         HandlingRequestUpdateRecurrenceView.as_view(),
         name='handling_request_update_recurrence'),

    path('handling/requests/cancel_recurrence/<int:pk>/',
         HandlingRequestCancelRecurrenceView.as_view(),
         name='handling_request_cancel_recurrence'),

    path('requests/<int:handling_request_id>/conversation_create/',
         HandlingRequestConversationCreateView.as_view(),
         name='handling_request_chat_create'),

    # S&F Request Documents
    path('requests/<int:handling_request_id>/documents_ajax/',
         HandlingRequestDocumentsListAjaxView.as_view(), name='request_documents_ajax'),
    path('requests/<int:handling_request_id>/create_document/',
         HandlingRequestDocumentCreateView.as_view(), name='request_documents_create'),
    path('requests/documents/<int:pk>/update/',
         HandlingRequestDocumentUpdateView.as_view(), name='request_document_update'),
    path('requests/documents/<int:pk>/history/',
         HandlingRequestDocumentHistoryView.as_view(), name='request_document_history'),

    # Missions
    path('missions_ajax/', MissionsListAjaxView.as_view(), name='missions_list_ajax'),
    path('missions/', MissionsListView.as_view(), name='missions_list'),
    path('missions/create/', MissionCreateUpdateView.as_view(), name='missions_create'),
    path('missions/calendar_json/', MissionsCalendarJsonResponse.as_view(), name='missions_calendar_json'),
    path('missions/calendar/', MissionsCalendarView.as_view(), name='missions_calendar'),
    path('missions/daily_schedule/', MissionDailyScheduleView.as_view(), name='missions_daily_schedule'),
    path('missions/<int:pk>/', MissionDetailsView.as_view(), name='missions_details'),
    path('missions/<int:pk>/update/', MissionCreateUpdateView.as_view(), name='missions_update'),
    path('missions/<int:pk>/update_callsign/', MissionCallsignUpdateView.as_view(), name='missions_update_callsign'),
    path('missions/<int:pk>/update_mission_number/', MissionNumberUpdateView.as_view(),
         name='missions_update_mission_number'),
    path('missions/<int:pk>/update_tail_number/', TailNumberUpdateView.as_view(),
         name='missions_update_tail_number'),
    path('missions/<int:pk>/update_aircraft_type/', MissionAircraftTypeUpdateView.as_view(),
         name='missions_update_aircraft_type'),
    path('missions/<int:pk>/update_apacs_number/', MissionApacsNumberUpdateView.as_view(),
         name='missions_update_apacs_number'),
    path('missions/<int:pk>/update_apacs_url/', MissionApacsUrlUpdateView.as_view(),
         name='missions_update_apacs_url'),
    path('missions/<int:pk>/confirm/', MissionConfirmationView.as_view(),
         name='missions_confirm'),
    path('missions/<int:pk>/cancel/', MissionCancellationView.as_view(),
         name='missions_cancel'),
    path('missions/<int:pk>/update_crew/', MissionCrewUpdateView.as_view(),
         name='missions_update_crew'),
    path('missions/<int:pk>/conversation_create/', MissionConversationCreateView.as_view(),
         name='mission_chat_create'),
    path('missions/<int:pk>/amend_timings/', MissionAmendTimingsView.as_view(),
         name='mission_amend_timings'),
    path('missions/<int:pk>/mission_packet_pdf/', MissionPacketPdfView.as_view(),
         name='mission_packet_pdf'),
    path('missions/<int:pk>/passengers/', MissionPassengersUpdateView.as_view(), name='missions_update_passengers'),
    path('missions/<int:pk>/cargo/', MissionCargoUpdateView.as_view(), name='missions_update_cargo'),

    # Mission Documents
    path('missions/<int:pk>/documents_ajax/', MissionDocumentsListAjaxView.as_view(),
         name='missions_documents_ajax'),
    path('missions/<int:pk>/documents/create/', MissionDocumentCreateView.as_view(),
         name='missions_documents_create'),
    path('missions/documents/<int:pk>/update/', MissionDocumentUpdateView.as_view(),
         name='missions_documents_update'),
    path('missions/documents/<int:pk>/history/', MissionDocumentHistoryView.as_view(),
         name='missions_documents_history'),

    path('missions/leg/<int:pk>/quick_edit/', MissionLegQuickEditView.as_view(),
         name='missions_leg_quick_edit'),
    path('missions/leg/<int:pk>/change_aircraft/', MissionLegChangeAircraftView.as_view(),
         name='missions_leg_change_aircraft'),
    path('missions/leg/<int:pk>/cancel/', MissionLegCancelView.as_view(),
         name='missions_leg_cancel'),

    # People
    path('people/person/<int:person_id>/travel_document_status/',
         PersonTravelDocumentStatusView.as_view(),
         name='person_travel_document_status'),

]
