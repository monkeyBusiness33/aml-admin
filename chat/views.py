from django.db.models import Q, OuterRef, Subquery
from django.views.generic import TemplateView
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from datetime import datetime, timedelta

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from sql_util.aggregates import SubqueryCount, Exists

from api.serializers.user import PersonSerializer, UserSettingsSerializer
from user.mixins import AdminPermissionsMixin
from .consumers import send_conversation_details_update
from .models import Conversation, Message, PeopleOnline
from .serializers import ConversationSerializer, MessageSerializer


class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class MetaInformationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, ]
    renderer_classes = [JSONRenderer]
    pagination_class = None

    def list(self, request):
        person_data = PersonSerializer(self.request.user.person, many=False).data
        data = {
            'person': person_data,
            'settings': UserSettingsSerializer(self.request.user.settings, many=False).data,
        }
        return Response(data)


class ConversationViewSet(ListModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = ConversationSerializer
    queryset = Conversation.objects.none()
    lookup_field = "pk"
    renderer_classes = [JSONRenderer]
    pagination_class = None

    def get_queryset(self):
        request_person = self.request.user.person
        latest_message_sq = Message.objects.filter(conversation_id=OuterRef('pk')).order_by('-timestamp')
        queryset = Conversation.objects.get_person_conversations(person=request_person).prefetch_related(
            'people',
            'people__details',
            'people__user',
            'messages',
            'messages__author',
            'messages__author__details',
            'messages__author__user',
            'messages__seen_by',
            'handling_request__airport',
            'mission',
        ).annotate(
            latest_message_text_val=Subquery(latest_message_sq.values('content')[:1]),
            latest_message_date_val=Subquery(latest_message_sq.values('timestamp')[:1]),
            is_person_participant_val=Exists('people', filter=Q(person=request_person)),
            unread_messages_count_val=SubqueryCount('messages',
                                                    filter=(~Q(author=request_person) & ~Q(seen_by=request_person)),
                                                    distinct=True),
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Return only chats with activity in last 31 days
        delta_30_days = datetime.now() - timedelta(days=31)
        queryset = queryset.exclude(latest_message_date_val__lt=delta_30_days)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        conversation.people.add(request.user.person_id, through_defaults={})
        serializer = ConversationSerializer(conversation, context={"person": request.user.person})

        send_conversation_details_update(channel_layer=get_channel_layer(),
                                         conversation=conversation,
                                         people=conversation.online_people)

        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        conversation.people.remove(request.user.person_id)
        serializer = ConversationSerializer(conversation, context={"person": request.user.person})

        send_conversation_details_update(channel_layer=get_channel_layer(),
                                         conversation=conversation,
                                         people=conversation.online_people)

        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        conversation = self.get_object()
        channel_layer = get_channel_layer()

        for person_online in PeopleOnline.objects.all():
            async_to_sync(channel_layer.group_send)(
                f'person_channel_{person_online.person.pk}',
                {
                    "type": "conversation_delete",
                    "conversation_id": conversation.pk,
                },
            )

        self.perform_destroy(conversation)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        return {"request": self.request, "person": self.request.user.person}


class MessagesFilter(filters.FilterSet):
    conversation = filters.CharFilter(field_name='conversation_id')
    older_than = filters.DateTimeFilter(lookup_expr="lte", field_name='timestamp')


class MessageViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = MessageSerializer
    queryset = Message.objects.with_details().order_by("-timestamp")
    renderer_classes = [JSONRenderer]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MessagesFilter
    pagination_class = MessagePagination

    def get_queryset(self):
        perms_q = Q()
        if not self.request.user.is_staff:
            perms_q = Q(conversation__people=self.request.user.person)

        queryset = Message.objects.with_details().prefetch_related(
            'author__details',
            'author__user',
            'seen_by',
        ).filter(
            perms_q
        ).order_by("-timestamp")
        return queryset


class StaffChatView(AdminPermissionsMixin, TemplateView):
    template_name = 'staff_chat.html'
    permission_required = []

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        return context
