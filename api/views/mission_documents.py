from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer

from handling.models import HandlingRequestDocument

from ..serializers.handling_documents import HandlingRequestDocumentSerializer


class MissionDocumentsList(generics.ListAPIView):
    """
    | Endpoint return list of documents attached to the Mission
    | URI: /missions/<mission_id>/documents/
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestDocumentSerializer

    def get_queryset(self):
        mission_id = self.kwargs['mission_id']
        person = getattr(self.request.user, 'person')

        qs = HandlingRequestDocument.objects.select_related(
            'type',
            'created_by',
        ).prefetch_related(
            'files',
            'files__uploaded_by'
        ).filter(
            Q(mission_id=mission_id) |
            Q(mission_leg__mission_id=mission_id) |
            Q(handling_request__mission_turnaround__mission_leg__mission_id=mission_id)
        )

        if not self.request.user.is_staff:
            position = person.primary_dod_position
            missions = position.get_missions_list()
            qs = qs.filter(
                Q(is_dod_viewable=True),
                Q(mission__in=missions) |
                Q(mission_leg__mission__in=missions) |
                Q(handling_request__mission_turnaround__mission_leg__mission__in=missions)
            )

        return qs
