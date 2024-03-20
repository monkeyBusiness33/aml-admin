from rest_framework import generics
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.exceptions import NotFound

from api.serializers.handling_request_crew import HandlingRequestCrewMemberPositionSerializer, \
    HandlingRequestCrewSerializer
from handling.models import HandlingRequestCrewMemberPosition, HandlingRequestCrew


class HandlingRequestCrewPositionsView(generics.ListAPIView):
    """
    | "Handling Request Crew Positions" endpoint
    | URI: /api/v1/handling_requests/crew_positions/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = None

    serializer_class = HandlingRequestCrewMemberPositionSerializer
    queryset = HandlingRequestCrewMemberPosition.objects.all()


class HandlingRequestCrewView(generics.ListCreateAPIView):
    """
    | "Handling Request Crew" [GET/POST] endpoint
    | URI: /api/v1/handling_request/<handling_request_id>/crew/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = None

    serializer_class = HandlingRequestCrewSerializer

    def get_queryset(self):
        handling_request_id = self.kwargs['handling_request_id']

        # Make able to get crew list only for users who have management permissions on S&F Request
        if not self.request.user.is_staff:
            person = getattr(self.request.user, 'person')
            position = person.primary_dod_position
            qs = position.get_sfr_list(managed=True)
            if not qs.filter(pk=handling_request_id).exists():
                raise NotFound

        qs = HandlingRequestCrew.objects.filter(
            handling_request_id=handling_request_id,
        )

        qs = qs.order_by('is_primary_contact')
        return qs


class HandlingRequestCrewUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    | "Handling Request Crew" [PATCH/DELETE] endpoint
    | URI: /api/v1/handling_request/crew/<crew_id>/
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = None

    serializer_class = HandlingRequestCrewSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            person = getattr(self.request.user, 'person')
            position = person.primary_dod_position
            qs = position.get_sfr_list(managed=True)
            if not qs.filter(mission_crew__pk=self.kwargs['pk']).exists():
                raise NotFound

        qs = HandlingRequestCrew.objects.filter(
            is_primary_contact=False,
        )
        return qs
