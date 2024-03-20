from django.http import HttpResponse
from rest_framework import filters, status
from django.db.models.aggregates import Max
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_json_api import pagination

from api.mixins import IsDoDPlannersUser
from api.serializers.handling_admin import HandlingRequestCalendarSerializer
from api.serializers.sfr_cache import HandlingRequestsOfflineCacheSerializer
from chat.models import Conversation
from chat.serializers import ConversationSerializer
from chat.utils.conversations import handling_request_create_conversation
from handling.serializers import *
from handling.models import *
from rest_framework import mixins, generics
from django.utils import timezone
from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, DateField, Case, When, OuterRef, Exists
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from datetime import datetime, timedelta

from handling.shared_views.handling_requests_calendar import HandlingRequestsListCalendarApiMixin
from handling.utils.handling_request_pdf import generate_handling_request_pdf


class HandlingRequestCreate(generics.CreateAPIView):
    '''
    Handling Request submitting endpoint
     URI: /handling_request
    '''

    serializer_class = HandlingRequestSerializer


class HandlingRequestUpdate(generics.RetrieveUpdateAPIView):
    """
    | S&F Request update (amend) endpoint
    | URI: [GET/PUT/PATCH] /handling_requests/<id>/
    """
    serializer_class = HandlingRequestSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        qs = position.get_sfr_list(managed=True)
        qs = qs.with_eta_etd_and_status_index()
        qs = qs.annotate(
            is_editable=Case(
                When(Q(pk__in=qs) & Q(eta_date__gte=timezone.now()), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        return qs


class HandlingRequestUpdateApacsNumberApiView(generics.UpdateAPIView):
    # TODO: Deprecated 2022-08-12
    """
    | Update S&F Request APACS Number
    | URI: /handling_request/<id>/
    """

    serializer_class = HandlingRequestUpdateApacsNumberSerializer
    lookup_field = 'pk'
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        qs = position.get_sfr_list(managed=True)
        qs = qs.filter(cancelled=False).all()
        return qs


class HandlingRequestUpdateApacsNumber(generics.UpdateAPIView):
    """
    | Update S&F Request Diplomatic Clearance Number
    | URI: handling_request/<id>/update_apacs_number/
    """

    serializer_class = HandlingRequestUpdateApacsNumberSerializerNew
    lookup_field = 'pk'
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        qs = position.get_sfr_list(managed=True)
        qs = qs.with_eta_etd_and_status_index()

        qs = qs.annotate(
            is_editable=Case(
                When(pk__in=qs, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        qs = qs.filter(cancelled=False).all()
        return qs


class HandlingRequestAircraftOnGroundApiView(generics.UpdateAPIView):
    """
    | Set AOG for the S&F Request
    | URI: handling_request/<id>/aog/
    """
    serializer_class = HandlingRequestAircraftOnGroundSerializer
    lookup_field = 'pk'
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        if self.request.user.is_staff:
            qs = HandlingRequest.objects.all()
        else:
            person = getattr(self.request.user, 'person')
            position = person.primary_dod_position
            qs = position.get_sfr_list(managed=True)

        qs = qs.with_eta_etd_and_status_index()
        qs = qs.filter(is_aog=False)
        return qs


class HandlingRequestAircraftServiceableApiView(generics.UpdateAPIView):
    """
    | Unset AOG for the S&F Request
    | URI: handling_request/<id>/aircraft_serviceable/
    """
    serializer_class = HandlingRequestAircraftServiceableSerializer
    lookup_field = 'pk'
    renderer_classes = [JSONRenderer]

    def get_object(self):
        if self.request.user.is_staff:
            qs = HandlingRequestMovement.objects.filter(request__is_aog=True)
        else:
            person = getattr(self.request.user, 'person')
            position = person.primary_dod_position
            managed_requests = position.get_sfr_list(managed=True)
            qs = HandlingRequestMovement.objects.filter(
                request__is_aog=True,
                request__in=managed_requests)

        obj = get_object_or_404(qs, request_id=self.kwargs['pk'], direction_id='DEPARTURE')
        return obj


class HandlingRequestsList(generics.ListAPIView):
    """
    | All S&F Requests list visible for Person
    | URI: /handling_requests/
    """
    serializer_class = HandlingRequestSerializer
    pagination_class = None

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        if not position:
            return []

        managed_missions = position.get_sfr_list(managed=True)
        qs = position.get_sfr_list()
        qs = qs.with_eta_etd_and_status_index()

        qs = qs.annotate(
            is_editable=Case(
                When(pk__in=managed_missions, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

        qs = qs.select_related(
            'type',
            'tail_number',
            'airport',
            'airport__details',
            'airport__airport_details',
            'handling_agent',
            'handling_agent__details',
            'handling_agent__handler_details',
            'aircraft_type',
            'created_by',
            'created_by__details',
            'created_by__details__title',
            'fuel_required',
            'fuel_unit',
            'fuel_booking',
            'fuel_booking__ipa',
            'fuel_booking__ipa__details',
        ).prefetch_related(
            'mission_crew',
            'mission_crew__person',
            'mission_crew__person__details',
            'mission_crew__position',
            'movement',
            'movement__airport',
            'movement__airport__details',
            'movement__airport__airport_details',
            'movement__hr_services',
            'movement__hr_services__service',
            'feedback',
        )

        qs = qs.order_by('status_index', 'eta_date')

        return qs


class HandlingRequestsListApiView(generics.ListAPIView):
    """
    | All S&F Requests list visible for Person
    | URI: /handling_requests/
    """
    serializer_class = HandlingRequestSerializer
    pagination.PageNumberPagination.page_size = 50
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        if not position:
            return []

        search_term = self.request.query_params.get('search')
        search_q = Q()
        if search_term:
            search_q = Q(
                Q(callsign__icontains=search_term) |
                Q(mission_number__icontains=search_term) |
                Q(airport__airport_details__icao_code__icontains=search_term)
            )

        managed_missions = position.get_sfr_list(managed=True)
        qs = position.get_sfr_list()
        qs = qs.with_eta_etd_and_status_index()
        qs = qs.filter(search_q)

        qs = qs.annotate(
            is_editable=Case(
                When(pk__in=managed_missions, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

        qs = qs.select_related(
            'type',
            'tail_number',
            'airport',
            'airport__details',
            'airport__airport_details',
            'handling_agent',
            'handling_agent__details',
            'handling_agent__handler_details',
            'aircraft_type',
            'created_by',
            'created_by__details',
            'created_by__details__title',
            'fuel_required',
            'fuel_unit',
            'fuel_booking',
            'fuel_booking__ipa',
            'fuel_booking__ipa__details',
        ).prefetch_related(
            'mission_crew',
            'mission_crew__person',
            'mission_crew__person__details',
            'mission_crew__position',
            'movement',
            'movement__airport',
            'movement__airport__details',
            'movement__airport__airport_details',
            'movement__hr_services',
            'movement__hr_services__service',
            'feedback',
        )

        qs = qs.order_by('status_index', 'eta_date')

        return qs


class HandlingRequestsOfflineCacheApiView(generics.ListAPIView):
    serializer_class = HandlingRequestsOfflineCacheSerializer
    renderer_classes = [JSONRenderer]
    pagination_class = None

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        if not position:
            return []

        qs = position.get_sfr_list()
        qs = qs.with_eta_etd_and_status_index()
        qs = qs.filter(
            ~Q(fuel_booking__isnull=True) & ~Q(fuel_booking__fuel_release=''),
            etd_date__gte=timezone.now() - timedelta(days=32)
        )

        qs = qs.order_by('eta_date')

        return qs


class HandlingRequestsCalendarView(generics.ListAPIView, HandlingRequestsListCalendarApiMixin):
    """
    | S&F Requests Calendar
    | URI: /handling_requests_calendar/
    """
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestCalendarSerializer
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        if not position:
            return []

        qs = position.get_sfr_list()
        self.queryset = qs.detailed_list()
        qs = super().get_queryset()
        return qs


class HandlingServicesListView(generics.ListAPIView):
    """
    View returns non paginated list of all Handling Services
    """
    serializer_class = HandlingServiceSerializer
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        person = self.request.user.person
        organisation = person.main_organisation
        organisation_id = self.request.query_params.get('organisation_id')
        location_id = self.request.query_params.get('location_id')
        codename = self.request.query_params.get('codename')

        if self.request.user.is_staff:
            organisation = Organisation.objects.filter(pk=organisation_id).first()

        location_q = Q()
        if location_id:
            location_q = (Q(hs_availability=None) | Q(hs_availability__airport_id=location_id))

        codename_q = Q(codename=codename) if codename else Q()

        qs = HandlingService.objects.dod_all(organisation=organisation).prefetch_related(
            'dla_service',
            'dla_service__spf_services',
            'quantity_selection_uom',
        ).filter(
            location_q,
            codename_q,
        ).order_by('name').distinct()
        return qs


class UpcomingFlightsListView(APIView):
    """
    View returns upcoming flights
    """
    renderer_classes = [JSONRenderer]

    def get(self, request, format=None):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        date_until = datetime.now() + timedelta(days=7)

        missions = position.get_sfr_list()

        movements = HandlingRequestMovement.objects.filter(
            request__callsign=OuterRef('callsign'),
            request__in=missions).values('date')

        aircard_set = missions.filter(
            callsign=OuterRef('callsign'),
            air_card_number__isnull=False,
        ).values('id')

        qs = missions.values(
            'callsign', 'air_card_prefix', 'air_card_number', 'air_card_expiration', 'air_card_photo',
        ).annotate(
            air_card_set=Exists(Subquery(aircard_set[:1])),
            trip_start=Subquery(movements.order_by('date')[:1]),
            trip_end=Subquery(movements.order_by('-date')[:1])
        ).exclude(trip_end__gt=date_until).order_by('callsign').distinct()

        return Response(qs)


class SetAirCardView(generics.CreateAPIView):
    """
    View able to set user's handling request Air Card details by callsign
    """
    serializer_class = SetAirCardSerializer
    renderer_classes = [JSONRenderer]


class ServiceProvisionFormToCompleteView(APIView):
    """
    | View returns list of trips that require SPF to complete
    | URI: /spf_to_complete/
    """
    renderer_classes = [JSONRenderer]

    def get(self, request, format=None):
        from handling.serializers import ServiceProvisionFormToCompleteSerializer
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        date_30_days_ago = datetime.now() - timedelta(days=30)
        movements = HandlingRequestMovement.objects.filter(request_id=OuterRef('pk')).values('date')

        missions = position.get_sfr_list(managed=True)

        qs = HandlingRequest.objects.with_status().select_related(
            'airport',
        ).prefetch_related('movement', 'spf').filter(
            pk__in=missions, status=4
        ).annotate(
            spf_count=Count('spf')
        ).annotate(
            spf_complete=Case(
                When(spf_count__gt=0, then=True),
                default=False
            ),
            trip_start=Subquery(movements.order_by('date')[:1]),
            trip_end=Subquery(movements.order_by('-date')[:1])
            ).exclude(
            Q(spf_complete=True) & Q(trip_end__lt=date_30_days_ago)
        ).order_by('callsign').distinct()

        data = ServiceProvisionFormToCompleteSerializer(qs, many=True).data
        return Response(data)


class ServiceProvisionFormSubmitView(generics.CreateAPIView, generics.UpdateAPIView):
    """
    | SPF Submission view
    | URI: /spf_submit/
    """
    serializer_class = ServiceProvisionFormSerializer
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    lookup_field = 'handling_request'

    def get_queryset(self):
        # QuerySet used in update() method (PATCH)
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        missions = position.get_sfr_list(managed=True)

        qs = ServiceProvisionForm.objects.filter(
            handling_request__in=missions).all()
        return qs


class HandlingRequestTypesListView(generics.ListAPIView):
    """
    | View returns non paginated list of all Handling Request Types
    | URI: /handling_requests/types/
    """

    serializer_class = HandlingRequestTypeSerializer
    queryset = HandlingRequestType.objects.all()
    pagination_class = None
    renderer_classes = [JSONRenderer]


class HandlingRequestCheckForDuplicateView(APIView):
    """
    | View returns boolean value for the existing handling request details
    | URI: /handling_requests/check_for_duplicates/
    """
    renderer_classes = [JSONRenderer]

    def post(self, request, *args, **kwargs):
        serializer = HandlingRequestCheckForDuplicateSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        exists, callsign, = serializer.check_for_duplicate()

        data = {
            'exists': exists,
            'callsign': callsign
        }
        return Response(data)


class HandlingRequestFeedbackCreateView(generics.CreateAPIView):
    # TODO: Deprecated 2022-08-12
    """
    | View to submit handling request feedback
    | URI: /handling_request/<id>/submit_feedback/
    """
    serializer_class = HandlingRequestFeedbackSerializer
    renderer_classes = [JSONRenderer]


class HandlingRequestFeedbackDetailedCreateView(generics.CreateAPIView):
    """
    | View to submit handling request feedback
    | URI: /handling_request/<id>/submit_feedback_detailed/
    """
    serializer_class = HandlingRequestDetailedFeedbackSerializer
    renderer_classes = [JSONRenderer]


class HandlingRequestsFeedbackListView(generics.ListAPIView):
    """
    | View returns Handling Requests feedback from user's organisation network
    | URI: /handling_requests/feedback/?search=EGKB
    """
    serializer_class = HandlingRequestFeedbackSerializer
    renderer_classes = [JSONRenderer]
    pagination_class = None
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        person = getattr(self.request.user, 'person')
        user_organisation = person.organisations.first()
        search_term = self.request.query_params.get('search')

        if search_term:
            search_term_q = (
                Q(handling_request__airport__airport_details__icao_code=search_term) |
                Q(handling_request__airport__airport_details__iata_code=search_term)
                )
        else:
            search_term_q = Q()

        qs = HandlingRequestFeedback.objects.filter(
            Q(handling_request__customer_organisation=user_organisation) |
            Q(handling_request__customer_organisation__details__department_of=user_organisation) |
            Q(handling_request__customer_organisation__details__department_of=user_organisation.details.department_of)
        ).filter(search_term_q)
        return qs


class HandlingRequestUpdatePrimaryContactView(generics.ListCreateAPIView):
    """
    | View update S&F Request Primary Contact
    | URI: /api/v1/handling_request/<handling_request_id>/primary_contact/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsDoDPlannersUser, ]
    pagination_class = None
    serializer_class = HandlingRequestUpdatePrimaryContactSerializer

    def get_queryset(self):
        qs = HandlingRequestCrew.objects.filter(
            handling_request_id=self.kwargs['handling_request_id']
        )

        qs = qs.order_by('is_primary_contact')
        return qs


class HandlingRequestGetPdfView(APIView):
    """
    | S&F Reqeust Details PDf API endpoint
    | URI: /api/v1/handling_request/<handling_request_id>/get_details_pdf/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = None

    def get(self, request, pk):
        if not self.request.user.is_staff:
            person = getattr(self.request.user, 'person')
            position = person.primary_dod_position
            qs = position.get_sfr_list(managed=True)
            if not qs.filter(pk=pk).exists():
                raise NotFound

        handling_request = HandlingRequest.objects.include_payload_data().get(pk=pk)
        document_file = generate_handling_request_pdf(handling_request)

        response = HttpResponse(document_file['content'], content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={document_file["name"]}'

        return response


class HandlingRequestConversationCreateApiView(APIView):
    """
    | Create S&F Request Chat Conversation
    | URI: /api/v1/handling_request/<handling_request_id>/conversation_create/
    """
    serializer_class = ConversationSerializer
    renderer_classes = [JSONRenderer]

    def post(self, request, handling_request_id):
        handling_request = get_object_or_404(HandlingRequest, pk=handling_request_id)

        conversation = handling_request_create_conversation(handling_request=handling_request,
                                                            author=request.user.person)

        serializer = ConversationSerializer(conversation, context={'person': request.user.person})
        response = Response(status=status.HTTP_200_OK, data=serializer.data)
        return response
