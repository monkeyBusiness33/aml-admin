from datetime import timedelta

from django.db.models import Q, Case, When, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.mixins import UpdateModelMixin, RetrieveModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from api.serializers.mission import MissionSerializer, MissionListSerializer, MissionLegCancelSerializer, \
    MissionsSetAirCardSerializer, MissionLegCancellationReasonSerializer, MissionLegDelaySerializer, \
    MissionAirCardSerializer, MissionLegAirCardSerializer, MissionGroundServicingSerializer, \
    MissionLegAmendTimingsSerializer
from chat.serializers import ConversationSerializer
from chat.utils.conversations import mission_create_conversation
from mission.models import Mission, MissionLeg, MissionLegCancellationReason, MissionTurnaround


class MissionQuerySetMixin(generics.GenericAPIView):
    """ Generate queryset to get person accessible Missions """
    def get_queryset(self):
        person = getattr(self.request.user, 'person')

        if self.request.user.is_staff:
            qs = Mission.objects.include_details()
        else:
            position = person.primary_dod_position
            qs = Mission.objects.filter(
                organisation=position.organisation,
            ).include_details()

        qs = qs.order_by('status_index', '-date_index',)
        return qs


class MissionLegQuerySetMixin(generics.GenericAPIView):
    """ Generate queryset to get person accessible Missions """
    def get_queryset(self):
        person = getattr(self.request.user, 'person')

        perms_q = Q()
        if not self.request.user.is_staff:
            position = person.primary_dod_position
            perms_q = Q(mission__organisation=position.organisation)

        qs = MissionLeg.objects.filter(perms_q)
        return qs


class MissionListApiView(generics.ListAPIView, MissionQuerySetMixin):
    serializer_class = MissionListSerializer
    renderer_classes = [JSONRenderer, ]


class MissionCreateApiView(generics.CreateAPIView):
    serializer_class = MissionSerializer
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


class MissionUpdateApiView(generics.UpdateAPIView, MissionQuerySetMixin):
    serializer_class = MissionSerializer
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


class MissionUpdateApiViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet, MissionQuerySetMixin):
    serializer_class = MissionSerializer
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


class MissionDetailsApiView(generics.RetrieveAPIView, MissionQuerySetMixin):
    serializer_class = MissionSerializer
    renderer_classes = [JSONRenderer, ]


class MissionLegCancelApiView(generics.UpdateAPIView, MissionLegQuerySetMixin):
    serializer_class = MissionLegCancelSerializer
    renderer_classes = [JSONRenderer, ]


class MissionLegDelayApiView(generics.UpdateAPIView, MissionLegQuerySetMixin):
    serializer_class = MissionLegDelaySerializer
    renderer_classes = [JSONRenderer, ]


class MissionConversationCreateApiView(APIView):
    """
    | Create Mission Chat Conversation
    | URI: /api/v1/missions/<mission_id>/conversation_create/
    """
    serializer_class = ConversationSerializer
    renderer_classes = [JSONRenderer]

    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, pk=mission_id)

        conversation = mission_create_conversation(mission=mission,
                                                   author=request.user.person)

        serializer = ConversationSerializer(conversation, context={'person': request.user.person})
        response = Response(status=status.HTTP_200_OK, data=serializer.data)
        return response


class UpcomingMissionsListView(APIView):
    """
    View returns upcoming missions
    """
    renderer_classes = [JSONRenderer]

    def get(self, request):
        person = getattr(self.request.user, 'person')
        position = person.primary_dod_position
        date_until = timezone.now() + timedelta(days=7)

        missions = position.get_missions_list()
        missions = missions.include_details()

        qs = missions.values(
            'callsign',
            'air_card_prefix',
            'air_card_number',
            'air_card_expiration',
            'air_card_photo',
            start_date=F('start_date_val'),
            end_date=F('end_date_val'),
        ).annotate(
            air_card_set=Case(
                When(air_card_number__isnull=False, then=True),
                default=False,
            ),
        ).exclude(end_date_val__gt=date_until).order_by('callsign').distinct()

        return Response(qs)


class MissionsSetAirCardView(generics.CreateAPIView):
    """
    View able to set user's handling request Air Card details by callsign
    """
    serializer_class = MissionsSetAirCardSerializer
    renderer_classes = [JSONRenderer]


class MissionLegCancellationReasonsListView(generics.ListAPIView):
    serializer_class = MissionLegCancellationReasonSerializer
    renderer_classes = [JSONRenderer, ]
    pagination_class = None

    def get_queryset(self):
        return MissionLegCancellationReason.objects.all()


class MissionAirCardUpdateApiView(generics.UpdateAPIView, MissionQuerySetMixin):
    serializer_class = MissionAirCardSerializer
    renderer_classes = [JSONRenderer, ]


class MissionLegAirCardUpdateApiView(generics.UpdateAPIView, MissionLegQuerySetMixin):
    serializer_class = MissionLegAirCardSerializer
    renderer_classes = [JSONRenderer, ]


class MissionLegAmendTimingsApiView(generics.UpdateAPIView, MissionLegQuerySetMixin):
    serializer_class = MissionLegAmendTimingsSerializer
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


class MissionGroundServicingApiView(generics.ListAPIView, generics.UpdateAPIView, MissionQuerySetMixin):
    serializer_class = MissionGroundServicingSerializer
    renderer_classes = [JSONRenderer, ]
    parser_classes = [JSONParser, ]
    pagination_class = None

    def get_object(self):
        mission = get_object_or_404(Mission, pk=self.kwargs['pk'])
        return mission

    def get_queryset(self):
        if self.request.user.is_staff:
            qs = MissionTurnaround.objects.filter(mission_leg__mission_id=self.kwargs['pk'])
        else:
            qs = Mission.objects.none()

        return qs

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response({'success': True})
