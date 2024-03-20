from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer

from handling.models import HandlingRequestDocumentType, HandlingRequestDocument

from ..serializers.handling_documents import HandlingRequestDocumentTypeSerializer, HandlingRequestDocumentSerializer, \
    HandlingRequestDocumentSignSerializer


class HandlingRequestDocumentTypesList(generics.ListAPIView):
    """
    | Admins Handling Requests list endpoint
    | URI: /handling_requests/documents/types/
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestDocumentTypeSerializer
    queryset = HandlingRequestDocumentType.objects.all()


class HandlingRequestDocumentsList(generics.ListAPIView):
    """
    | Endpoint return list of documents attached to the S&F Request
    | URI: /handling_request/<handling_request_id>/documents/
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None
    renderer_classes = [JSONRenderer]
    serializer_class = HandlingRequestDocumentSerializer

    def get_queryset(self):
        handling_request_id = self.kwargs['handling_request_id']
        person = getattr(self.request.user, 'person')

        qs = HandlingRequestDocument.objects.select_related(
            'type',
            'created_by',
        ).prefetch_related(
            'files',
            'files__uploaded_by'
        ).filter(
            handling_request_id=handling_request_id,
        )

        if not self.request.user.is_staff:
            position = person.primary_dod_position
            missions = position.get_sfr_list(managed=True)
            qs = qs.filter(
                is_dod_viewable=True,
                handling_request__in=missions,
            )

        return qs


class HandlingRequestDocumentCreateView(generics.CreateAPIView):
    """
    | Endpoint to submit S&F Request Document
    | URI: /handling_request/<handling_request_id>/documents/upload/
    """
    serializer_class = HandlingRequestDocumentSerializer
    renderer_classes = [JSONRenderer]


class HandlingRequestDocumentUpdateView(generics.UpdateAPIView):
    """
    | Endpoint to update S&F Request Document details and file
    | URI: /handling_requests/documents/<document_id>/update/
    """
    serializer_class = HandlingRequestDocumentSerializer
    renderer_classes = [JSONRenderer]
    queryset = HandlingRequestDocument.objects.all()


class HandlingRequestDocumentSignView(generics.UpdateAPIView):
    """
    | Endpoint to update S&F Request Document details and file
    | URI: /handling_requests/documents/<document_id>/sign/
    """
    serializer_class = HandlingRequestDocumentSignSerializer
    renderer_classes = [JSONRenderer]
    queryset = HandlingRequestDocument.objects.all()


class HandlingDocumentCreateView(generics.CreateAPIView):
    """
    | Endpoint to submit generic Handling Document
    | URI: /handling/documents/upload/
    """
    serializer_class = HandlingRequestDocumentSerializer
    renderer_classes = [JSONRenderer]


class HandlingDocumentUpdateView(generics.UpdateAPIView):
    """
    | Endpoint to update generic Handling Document details and file
    | URI: /handling/documents/<document_id>/update/
    """
    serializer_class = HandlingRequestDocumentSerializer
    renderer_classes = [JSONRenderer]
    queryset = HandlingRequestDocument.objects.all()
