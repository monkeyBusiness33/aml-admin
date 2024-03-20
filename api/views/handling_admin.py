from django.db.models import Q
from rest_framework import generics, status, filters
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from handling.serializers import HandlingRequestSerializer as ClientHandlingRequestSerializer
from handling.shared_views.handling_requests_calendar import HandlingRequestsListCalendarApiMixin
from ..mixins import IsSuperUser
from ..serializers.handling_admin import *
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.exceptions import NotFound


class HandlingRequestsList(generics.ListAPIView):
    """
    | Admins Handling Requests list endpoint
    | URI: /admin/handling_requests
    """
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        search_term = self.request.query_params.get('search')
        search_q = Q()
        if search_term:
            search_q = Q(
                Q(callsign__icontains=search_term) |
                Q(mission_number__icontains=search_term) |
                Q(airport__airport_details__icao_code__icontains=search_term)
            )

        qs = HandlingRequest.objects.with_eta_etd_and_status_index()

        qs = qs.prefetch_related(
            'airport', 'movement', 'movement__airport', 'movement__hr_services', 'movement__hr_services__service',
            'chat_conversations',
        ).order_by('-created_at').all()

        qs = qs.filter(search_q)
        qs = qs.order_by('status_index', 'eta_date')

        return qs


class HandlingRequestsCalendarView(generics.ListAPIView, HandlingRequestsListCalendarApiMixin):
    """
    | Admins Handling Requests list endpoint
    | URI: /admin/handling_requests_calendar
    """
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestCalendarSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = []

    def get_queryset(self):
        self.queryset = HandlingRequest.objects.detailed_list()
        qs = super().get_queryset()
        return qs


class HandlingRequestDetailsView(generics.RetrieveUpdateAPIView):
    """
    | Staff Handling Requests details and update view
    | URI: /ops/handling_request/<int:pk>/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    serializer_class = HandlingRequestSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        qs = HandlingRequest.objects.detailed_list()
        return qs


class HandlingRequestDetailsViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    | Staff Handling Requests details and update view
    | URI: /ops/handling_request/<int:pk>/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    serializer_class = HandlingRequestSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        qs = HandlingRequest.objects.detailed_list()
        return qs


class HandlingRequestServiceUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    | Staff Handling Request Services details, update and delete view
    | URI: /ops/handling_requests/service/<int:pk>/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    queryset = HandlingRequestServices
    serializer_class = HandlingRequestServicesSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated, IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_service_deletable:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise NotFound()


class HandlingRequestCustomServiceCreateView(generics.CreateAPIView):
    """
    | Endpoint to create "Custom Service" for S&F Request
    | URI: /admin/handling_requests/custom_service/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    serializer_class = HandlingRequestCustomServiceCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class HandlingRequestServiceAddView(generics.CreateAPIView):
    """
    | Staff Handling Request Add Service Endpoint
    | URI: /ops/handling_request/service_add/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    serializer_class = HandlingRequestServicesSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class HandlingRequestUpdateTailNumberView(generics.UpdateAPIView):
    """
    | Staff Handling Request Set Tail Number View
    | URI: /ops/handling_request/<int:pk>/update_tail_number/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    queryset = HandlingRequest
    serializer_class = HandlingRequestTailNumberSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated, IsAdminUser]


class HandlingReqeustTypesListView(generics.ListAPIView):
    """
    | S&F Requests types list
    | URI: /admin/handling_requests/types/
    """
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestTypeSerializer
    queryset = HandlingRequestType.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None


class HandlingRequestCreate(generics.CreateAPIView):
    """
    | Staff Handling Request submitting endpoint
    | URI: /admin/handling_request/
    """
    serializer_class = ClientHandlingRequestSerializer


class HandlingRequestIpaListCreateView(generics.ListCreateAPIView):
    """
    | Endpoint return list if IPA's available on the S&F Request airport
    | Or create new IPA [POST] for the S&F Request airport
    | URI: /api/v1/admin/handling_request/<handling_request_id>/ipas/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None

    serializer_class = FuelBookingIpaSerializer

    def get_queryset(self):
        handling_request = HandlingRequest.objects.get(pk=self.kwargs['handling_request_id'])
        qs = Organisation.objects.ipa().filter(ipa_locations=handling_request.airport.pk)
        return qs


class FuelBookingConfirmationView(generics.CreateAPIView, generics.UpdateAPIView):
    """
    | Staff "Handling Request Fuel Booking Confirmation" endpoint
    | URI: /api/v1/admin/handling_request/<handling_request_id>/fuel_booking_confirmation/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None
    serializer_class = FuelBookingSerializer

    def get_object(self):
        queryset = HandlingRequestFuelBooking.objects
        handling_request_id = self.kwargs['handling_request_id']
        obj = get_object_or_404(queryset, handling_request_id=handling_request_id)
        return obj


class HandlingRequestHandlerListCreateView(generics.ListCreateAPIView):
    """
    | Endpoint return list if IPA's available on the S&F Request airport
    | Or create new IPA [POST] for the S&F Request airport
    | URI: /api/v1/admin/handling_request/<handling_request_id>/ipas/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None

    serializer_class = HandlingRequestHandlerSerializer

    def get_queryset(self):
        handling_request = HandlingRequest.objects.get(pk=self.kwargs['handling_request_id'])
        qs = Organisation.objects.handling_agent().filter(handler_details__airport=handling_request.airport).all()
        return qs


class HandlingRequestPPRUpdateView(generics.UpdateAPIView):
    """
    | View to update S&F Request PPR Number
    | URI: /handling_request/<id>/update_ppr/
    """
    serializer_class = HandlingRequestPPRUpdateSerializer
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = HandlingRequest


class HandlingRequestUnableToSupportView(generics.UpdateAPIView):
    """
    | View to cancel (Unable To Support) S&F Request
    | URI: /handling_request/<id>/unable_to_support/
    """
    serializer_class = HandlingRequestUnableToSupportSerializer
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = HandlingRequest


class SendHandlingRequestView(generics.UpdateAPIView):
    """
    | Generate and submit AutoSPF
    | URI: /admin/handling_request/<handling_request_id>/send_handling_request/
    """
    serializer_class = SendHandlingRequestSerializer
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_url_kwarg = 'handling_request_id'

    def get_queryset(self):
        qs = HandlingRequest.objects.filter(
            handling_agent__isnull=False,
            auto_spf__isnull=True,
        )
        return qs


class HandlingRequestGroundHandlingConfirmationView(generics.UpdateAPIView):
    """
    | Confirm Ground Handler for S&F Request
    | URI: /handling_request/<handling_request_id>/ground_handling_confirmation/
    """
    serializer_class = HandlingRequestGroundHandlingConfirmationSerializer
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_url_kwarg = 'handling_request_id'

    def get_queryset(self):
        qs = HandlingRequest.objects.filter(
            handling_agent__isnull=False,
            auto_spf__isnull=False,
        )
        return qs


class HandlingRequestUpdateAirCardNumberView(generics.UpdateAPIView):
    """
    | SuperUsers Endpoint to Handling Request AirCard
    | URI: /ops/handling_request/<int:pk>/update_aircard_number/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    queryset = HandlingRequest
    serializer_class = HandlingRequestAirCardSerializer
    lookup_field = 'pk'
    permission_classes = [IsSuperUser]


class HandlingRequestUpdateMissionTypeView(generics.UpdateAPIView):
    """
    | SuperUsers Endpoint to Handling Request Mission type
    | URI: /ops/handling_request/<int:pk>/update_mission_type/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    queryset = HandlingRequest
    serializer_class = HandlingRequestUpdateMissionTypeSerializer
    lookup_field = 'pk'
    permission_classes = [IsSuperUser]


class HandlingRequestMovementUpdateView(generics.UpdateAPIView):
    """
    | SuperUsers Endpoint to update Handling Request Movement
    | URI: /api/v1/admin/handling_requests/movement/<movement_id>/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    queryset = HandlingRequestMovement
    serializer_class = HandlingRequestMovementSerializer
    lookup_field = 'pk'
    permission_classes = [IsSuperUser]
