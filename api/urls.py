from django.urls import path, re_path, include
from .views.auth import *
from .views.base_views import *
from .views.handling_documents import HandlingRequestDocumentTypesList, HandlingRequestDocumentCreateView, \
    HandlingRequestDocumentUpdateView, HandlingRequestDocumentsList, HandlingRequestDocumentSignView, \
    HandlingDocumentUpdateView, HandlingDocumentCreateView
from .views.handling_request_crew import (
    HandlingRequestCrewView,
    HandlingRequestCrewUpdateDeleteView,
    HandlingRequestCrewPositionsView,
)

from .views.meta import MetaInformationApiView
from .views.mission import MissionListApiView, MissionCreateApiView, MissionDetailsApiView, MissionLegCancelApiView, \
    MissionConversationCreateApiView, UpcomingMissionsListView, MissionsSetAirCardView, MissionUpdateApiView, \
    MissionLegCancellationReasonsListView, MissionLegDelayApiView, MissionAirCardUpdateApiView, \
    MissionLegAirCardUpdateApiView, MissionGroundServicingApiView, MissionLegAmendTimingsApiView, \
    MissionUpdateApiViewSet
from .views.mission_documents import MissionDocumentsList
from .views.organisation import *
from .views.handling import *
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework.routers import SimpleRouter

from .views.user import UserSettingsApiView

app_name = 'api'
urlpatterns = [

    # Includes
    path('organisations/', include('organisation.urls_api', namespace='organisations')),

    path('auth/', ObtainAuthToken.as_view(), name='api_auth'),
    path('meta/', MetaInformationApiView.as_view(), name='meta'),
    path('user/settings/', UserSettingsApiView.as_view(), name='user_settings'),
    path('devices/', FCMDeviceManagementView.as_view(
        {'post': 'create', 'delete': 'destroy'}), name='create_fcm_device'),

    # Base views
    path('aircraft_types/', AircraftTypesView.as_view(), name='aircraft_types'),
    path('organisation/aircraft_types/', AircraftTypesView.as_view(), name='organisation_aircraft_types'),
    path('quantity_units/', QuantityUnitsListView.as_view(), name='quantity_units'),
    path('uom/', UomListView.as_view(), name='uom_list'),
    path('airports/', AirportsListView.as_view(), name='airports_list'),
    path('handling_locations/', HandlingLocationsListView.as_view(), name='handling_locations_list'),
    path('locations/', ServicingAndFuelingLocationsListView.as_view(), name='locations_list'),
    path('aircraft/create/', AircraftCreateView.as_view(), name='aircraft_create'),
    path('aircard_prefixes/', AirCardPrefixesListView.as_view(), name='aircard_prefixes'),

    # Person & Organisation
    path('organisation/fleet/', OrganisationFleetView.as_view(), name='airports_list'),
    path('organisation/people/', OrganisationPeopleView.as_view(), name='airports_people'),

    # Handling
    path('handling_request/', HandlingRequestCreate.as_view(), name='handling_request_create'),
    path('handling_request/<int:pk>/submit_feedback_detailed/', HandlingRequestFeedbackDetailedCreateView.as_view(),),
    path('handling_requests/feedback/', HandlingRequestsFeedbackListView.as_view(), name='handling_request_feedback'),
    path('handling_request/<int:pk>/', HandlingRequestUpdate.as_view(), name='handling_request_update'),
    path('handling_request/<int:pk>/update_apacs_number_detailed/', HandlingRequestUpdateApacsNumber.as_view(), name='handling_request_update_apacs_num'),
    path('handling_request/<int:pk>/get_details_pdf/', HandlingRequestGetPdfView.as_view(), name='handling_request_get_pdf'),
    path('handling_request/<int:pk>/aog/', HandlingRequestAircraftOnGroundApiView.as_view(), name='handling_request_aog'),
    path('handling_request/<int:pk>/aircraft_serviceable/', HandlingRequestAircraftServiceableApiView.as_view(), name='handling_request_aircraft_serviceable'),
    path('handling_services/', HandlingServicesListView.as_view(), name='handling_services'),
    path('handling_requests/', HandlingRequestsList.as_view(), name='handling_requests'),
    path('handling_requests/offline_cache/', HandlingRequestsOfflineCacheApiView.as_view(), name='handling_requests_offline_cache'),
    path('handling_requests_list/', HandlingRequestsListApiView.as_view(), name='handling_requests_list'),
    path('handling_requests_calendar/', HandlingRequestsCalendarView.as_view(), name='handling_requests_calendar'),
    re_path('upcoming_flights/?$', UpcomingFlightsListView.as_view(), name='upcoming_flights'),
    path('upcoming_flights/set_aircard/', SetAirCardView.as_view(), name='set_aircard'),
    re_path('spf_to_complete/?$', ServiceProvisionFormToCompleteView.as_view(), name='spf_to_complete'),
    path('spf_submit/<int:handling_request>/', ServiceProvisionFormSubmitView.as_view(), name='spf_submit'),
    path('handling_requests/types/', HandlingRequestTypesListView.as_view(), name='handling_request_types'),
    path('handling_requests/check_for_duplicates/', HandlingRequestCheckForDuplicateView.as_view(), name='handling_request_check_for_duplicate'),

    # S&F Request Documents
    path('handling_requests/documents/types/',
         HandlingRequestDocumentTypesList.as_view(),
         name='handling_requests_documents_types'),

    path('handling_request/<int:handling_request_id>/documents/',
         HandlingRequestDocumentsList.as_view(),
         name='handling_requests_documents'),

    path('handling_request/<int:handling_request_id>/documents/upload/',
         HandlingRequestDocumentCreateView.as_view(),
         name='handling_requests_documents_create'),

    path('handling_requests/documents/<int:pk>/update/',
         HandlingRequestDocumentUpdateView.as_view(),
         name='handling_requests_documents_update'),

    path('handling_requests/documents/<int:pk>/sign/',
         HandlingRequestDocumentSignView.as_view(),
         name='handling_requests_documents_sign'),

    # Mission Documents
    path('missions/<int:mission_id>/documents/',
         MissionDocumentsList.as_view(),
         name='mission_documents'),

    # Handling Documents
    path('handling/documents/upload/',
         HandlingDocumentCreateView.as_view(),
         name='handling_documents_create'),

    path('handling/documents/<int:pk>/update/',
         HandlingDocumentUpdateView.as_view(),
         name='handling_documents_update'),

    # S&F Request Crew
    path('handling_requests/crew_positions/', HandlingRequestCrewPositionsView.as_view(), name='handling_requests_crew_positions'),
    path('handling_request/<int:handling_request_id>/primary_contact/', HandlingRequestUpdatePrimaryContactView.as_view(), name='handling_request_update_primary_contact'),

    # S&F Request Crew (Manage Assigned Crew) client & staff endpoints
    path('handling_request/<int:handling_request_id>/crew/',
         HandlingRequestCrewView.as_view(),
         name='handling_request_crew'),

    path('handling_request/crew/<int:pk>/',
         HandlingRequestCrewUpdateDeleteView.as_view(),
         name='handling_request_crew_update_delete'),

    # Create S&F Request Chat Conversation
    path('handling_request/<int:handling_request_id>/conversation_create/',
         HandlingRequestConversationCreateApiView.as_view(),
         name='handling_request_create_conversation'),

    # TODO: Deprecated 2022-08-12
    path('handling_request/<int:pk>/update_apacs_number/', HandlingRequestUpdateApacsNumberApiView.as_view(), name='handling_request_update_apacs_number'),
    path('handling_request/<int:pk>/submit_feedback/', HandlingRequestFeedbackCreateView.as_view(), name='handling_request_submit_feedback'),


    # Missions
    path('missions/', MissionListApiView.as_view(), name='missions'),
    path('missions/<int:pk>/update/', MissionUpdateApiView.as_view(), name='mission_update'),
    # path('missions/<int:pk>/', MissionDetailsApiView.as_view(), name='mission_details'),
    path('missions/<int:pk>/ground_servicing/', MissionGroundServicingApiView.as_view(),
         name='mission_ground_servicing'),
    path('missions/create/', MissionCreateApiView.as_view(), name='missions_create'),
    path('missions/leg/<int:pk>/cancel/', MissionLegCancelApiView.as_view(), name='mission_leg_cancel'),
    path('missions/leg/<int:pk>/delay/', MissionLegDelayApiView.as_view(), name='mission_leg_delay'),
    path('missions/leg/<int:pk>/update_aircard/', MissionLegAirCardUpdateApiView.as_view(),
         name='mission_leg_update_aircard'),
    path('missions/leg/<int:pk>/amend_timings/', MissionLegAmendTimingsApiView.as_view(),
         name='mission_leg_amend_timings'),
    path('missions/<int:mission_id>/conversation_create/', MissionConversationCreateApiView.as_view(),
         name='mission_conversation_create'),
    path('missions/<int:pk>/update_aircard/', MissionAirCardUpdateApiView.as_view(),
         name='mission_update_aircard'),
    path('missions/upcoming/', UpcomingMissionsListView.as_view(), name='missions_upcoming'),
    path('missions/set_air_card/', MissionsSetAirCardView.as_view(), name='missions_set_air_card'),
    path('missions/cancellation_resons/', MissionLegCancellationReasonsListView.as_view(),
         name='missions_legs_cancellation_reasons'),

]


class OptionalSlashRouter(SimpleRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '/?'


router = OptionalSlashRouter()
router.register("missions", MissionUpdateApiViewSet, basename='mission_details')
urlpatterns += router.urls
