from django.urls import path

from .views.handling import HandlingRequestConversationCreateApiView
from .views.handling_admin import *
from .views.base_admin_views import *
from api.views.organisation_admin import OrganisationsListView, OrganisationPeopleListView
from .views.handling_request_crew import (
    HandlingRequestCrewView,
    HandlingRequestCrewUpdateDeleteView,
    HandlingRequestCrewPositionsView,
)

from rest_framework.routers import DefaultRouter, SimpleRouter


class OptionalSlashRouter(SimpleRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '/?'


router = OptionalSlashRouter()

app_name = 'api_admin'
urlpatterns = [
    path('handling_requests/', HandlingRequestsList.as_view(), name='handling_requests'),
    path('handling_requests_calendar/', HandlingRequestsCalendarView.as_view(), name='handling_requests_calendar'),
    path('handling_request/', HandlingRequestCreate.as_view(), name='handling_request_create'),
    # path('handling_request/<int:pk>/', HandlingRequestDetailsView.as_view(), name='handling_request_details'),

    # S&F Request Crew
    # TODO: Crew uris deprecated 2022-10-18
    path('handling_requests/crew_positions/',
         HandlingRequestCrewPositionsView.as_view(),
         name='handling_requests_crew_positions'),

    path('handling_request/<int:handling_request_id>/crew/',
         HandlingRequestCrewView.as_view(),
         name='handling_request_crew'),

    path('handling_request/crew/<int:pk>/',
         HandlingRequestCrewUpdateDeleteView.as_view(),
         name='handling_request_crew_update_delete'),
    # TODO: Crew uris deprecated 2022-10-18

    path('handling_request/<int:pk>/update_tail_number/',
         HandlingRequestUpdateTailNumberView.as_view(),
         name='handling_request_update_tail_number'),

    # S&F Request Fuel Booking
    path('handling_request/<int:handling_request_id>/fuel_booking_confirmation/',
         FuelBookingConfirmationView.as_view(),
         name='handling_request_fuel_booking_confirmation'),

    path('handling_request/<int:handling_request_id>/ipas/',
         HandlingRequestIpaListCreateView.as_view(),
         name='handling_request_ipas'),

    # S&F Request Handler
    path('handling_request/<int:handling_request_id>/handlers/',
         HandlingRequestHandlerListCreateView.as_view(),
         name='handling_request_handler'),

    path('handling_request/<int:handling_request_id>/send_handling_request/',
         SendHandlingRequestView.as_view(),
         name='send_handling_request'),

    path('handling_request/<int:handling_request_id>/ground_handling_confirmation/',
         HandlingRequestGroundHandlingConfirmationView.as_view(),
         name='handling_request_ground_handling_confirmation'),

    # S&F Request Services
    path('handling_request/service_add/',
         HandlingRequestServiceAddView.as_view(),
         name='handling_request_service_add'),

    path('handling_requests/service/<int:pk>/',
         HandlingRequestServiceUpdateView.as_view(),
         name='handling_request_service'),

    path('handling_requests/custom_service/',
         HandlingRequestCustomServiceCreateView.as_view(),
         name='handling_service_create'),

    # S&F Request Update PPR
    path('handling_request/<int:pk>/update_ppr/',
         HandlingRequestPPRUpdateView.as_view(),
         name='handling_request_update_ppr'),

    # S&F Request AirCard
    path('handling_request/<int:pk>/update_aircard_number/',
         HandlingRequestUpdateAirCardNumberView.as_view(),
         name='handling_request_update_aircard_number'),

    # S&F Request Update Mission Type
    path('handling_request/<int:pk>/update_mission_type/',
         HandlingRequestUpdateMissionTypeView.as_view(),
         name='handling_request_update_mission_type'),

    # S&F Request Unable To Support
    path('handling_request/<int:pk>/unable_to_support/',
         HandlingRequestUnableToSupportView.as_view(),
         name='handling_request_unable_to_support',),

    # S&F Request Update Movement
    path('handling_requests/movement/<int:pk>/',
         HandlingRequestMovementUpdateView.as_view(),
         name='handling_request_update_movement',),

    # TODO: Deprecated 2023-06-01
    # https://aviationdatasolutions.slack.com/archives/C038P574EEN/p1685629757253819?thread_ts=1684445490.243559&cid=C038P574EEN
    # Create S&F Request Chat Conversation
    path('handling_request/<int:handling_request_id>/conversation_create/',
         HandlingRequestConversationCreateApiView.as_view(),
         name='handling_request_create_conversation'),

    path('handling_requests/types/', HandlingReqeustTypesListView.as_view(), name='handling_requests_types'),

    path('ipas/', IPAListView.as_view(), name='ipa_list'),
    path('organisations/', OrganisationsListView.as_view(), name='organisations'),
    path('organisation/<int:pk>/people/', OrganisationPeopleListView.as_view(), name='organisation_people'),
    path('organisation/<int:pk>/fleet/', OrganisationFleetView.as_view(), name='organisation_fleet'),

    path('organisation/<int:pk>/aircraft_types/',
         OrganisationAircraftTypesView.as_view(),
         name='organisation_aircraft_types'),
]

router.register("handling_request", HandlingRequestDetailsViewSet, basename='sfr_details')
urlpatterns += router.urls
