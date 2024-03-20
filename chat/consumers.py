from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.db.models import Q
from datetime import datetime

from api.serializers.user import PersonSerializer
from chat.models import Conversation, PeopleOnline, MessageSeenBy
from chat.serializers import MessageSerializer, ConversationSerializer
from chat.utils.unread_messages import get_person_unread_messages_count


def send_conversation_details_update(channel_layer, conversation, people):
    for person in people:
        async_to_sync(channel_layer.group_send)(
            f'person_channel_{person.pk}',
            {
                "type": "conversation_details",
                "conversation": ConversationSerializer(conversation,
                                                       context={'person': person}).data,
            },
        )


class ChatConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.user = None
        self.person = None

        self.conversation_id = None
        self.conversation = None

    def send_online_users(self):
        data = {
            'type': 'people_online',
            'message': list(PeopleOnline.objects.values_list('person_id', flat=True))
        }
        self.send_json(data)

    def process_read_messages(self):
        if self.conversation.people.filter(pk=self.person.pk).exists():
            mark_as_seen = self.conversation.messages.filter(
                ~Q(author=self.person) & ~Q(seen_by=self.person)
            )

            for message in mark_as_seen:
                MessageSeenBy.objects.update_or_create(
                    message=message, person=self.person,
                )

                async_to_sync(self.channel_layer.group_send)(
                    self.conversation.pk,
                    {
                        "type": "chat_message_update",
                        "message": MessageSerializer(message, many=False).data,
                    },
                )

        self.send_json(
            {
                "type": "conversation_details",
                "conversation": ConversationSerializer(self.conversation, context={'person': self.person}).data,
            }
        )

    def connect(self):
        self.accept()
        self.user = self.scope.get("user")

        if self.user is None or not self.user.is_authenticated:
            self.send_json(
                {
                    "error": "unauthenticated",
                    "message": "Wrong or empty token!",
                }
            )
            self.close(code=4003)
            return

        self.person = self.user.person

        # Send welcome message
        self.send_json(
            {
                "type": "welcome_message",
                "message": "Hey there! You've successfully connected!",
            }
        )

        self.conversation_id = f"{self.scope['url_route']['kwargs']['conversation_id']}"

        # Get requested conversation
        self.conversation = Conversation.objects.get_person_conversations(person=self.person).filter(
            pk=self.conversation_id,
        ).first()

        if not self.conversation:
            self.send_json(
                {
                    "error": "no_conversation",
                    "message": "Conversation does not exists or inaccessible for user",
                }
            )

        # Join conversation group conversation
        async_to_sync(self.channel_layer.group_add)(
            self.conversation_id,
            self.channel_name,
        )

        # Join personal group (for system messages)
        async_to_sync(self.channel_layer.group_add)(
            f'person_channel_{self.person.pk}',
            self.channel_name,
        )

        # Set online status
        self.person.chat_online.get_or_create(defaults={'channel_name': self.channel_name})
        self.send_online_users()

        # Send recent messages history
        unread_messages = self.conversation.messages.filter(~Q(seen_by=self.person)).count()
        messages_to_return = unread_messages if unread_messages >= 50 else 50
        messages = self.conversation.messages.with_details().prefetch_related(
            'author__details',
            'author__user',
            'seen_by',
        ).order_by("-timestamp")[0:messages_to_return]
        message_count = self.conversation.messages.all().count()
        self.send_json(
            {
                "type": "recent_messages",
                "messages": MessageSerializer(reversed(messages), many=True).data,
                "has_more": message_count > messages_to_return,
            }
        )

        # Aware messages as seen by person
        self.process_read_messages()

    def disconnect(self, code):
        if self.person:
            self.person.chat_online.all().delete()
            self.send_online_users()

        return super().disconnect(code)

    def receive_json(self, content, **kwargs):
        message_type = content.get("type")
        if not message_type:
            self.send_json(
                {
                    "error": "unknown_message_type",
                    "message": "Please specify correct message type",
                }
            )

        if message_type == "typing":
            async_to_sync(self.channel_layer.group_send)(
                self.conversation.pk,
                {
                    "type": "typing",
                    "conversation_id": self.conversation_id,
                    "person": PersonSerializer(self.person, many=False).data,
                    "typing": content["typing"],
                },
            )

        if message_type == "chat_message":
            message_id = content.get("message_id")

            # Debugging
            if content["message"] == 'disconnect':
                self.close()

            self.conversation.messages.create(
                pk=message_id,
                author=self.person,
                content=content["message"],
            )

            # Add Person to Conversation
            self.conversation.people.add(self.person)

        if message_type == "read_messages":
            self.process_read_messages()

        return super().receive_json(content, **kwargs)

    def typing(self, event):
        self.send_json(event)

    def recent_messages(self, event):
        self.send_json(event)

    def chat_message(self, event):
        self.send_json(event)

    def conversation_details(self, event):
        self.send_json(event)

    def chat_message_update(self, event):
        self.send_json(event)

    def read_messages(self, event):
        self.send_json(event)

    def conversation_delete(self, event):
        self.send_json(event)

    def user_settings(self, event):
        self.send_json(event)


def get_notifications_data(person):
    resp = {'type': 'notifications_data'}

    # Add permissions checking
    if person.user.has_perm('handling.p_dod_comms'):
        resp['unread_messages'] = get_person_unread_messages_count(person)

    # Datetime
    current_time = datetime.utcnow().strftime("%H:%MZ %b-%d-%Y").upper()
    current_time += f' (Day {int(datetime.utcnow().strftime("%j"))})'
    resp['current_time'] = current_time

    from handling.models import HandlingRequest
    if person.user.has_perm('handling.p_view'):
        resp['handling_requests'] = HandlingRequest.objects.with_status().filter(status=10).count()
        resp['unread_notes'] = person.comments_read_statuses.filter(is_read=False).count()

    if person.user.has_perm('handling.p_spf_v2_reconcile'):
        resp['spf_to_reconcile'] = HandlingRequest.objects.spf_to_reconcile().count()

    return resp


class NotificationsConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.user = None
        self.person = None

    def send_online_users(self):
        data = {
            'type': 'people_online',
            'message': list(PeopleOnline.objects.values_list('person_id', flat=True))
        }
        self.send_json(data)

    def connect(self):
        self.accept()
        self.user = self.scope.get("user")

        if self.user is None or not self.user.is_authenticated:
            self.send_json(
                {
                    "error": "unauthenticated",
                    "message": "Wrong or empty token!",
                }
            )
            self.close(code=4003)
            return None

        self.person = self.user.person

        # Send welcome message
        self.send_json(
            {
                "type": "welcome_message",
                "message": "Hey there! You've successfully connected!",
            }
        )

        # Set online status
        # self.person.chat_online.get_or_create(defaults={'channel_name': self.channel_name})
        # self.send_online_users()

        # Join personal notifications group
        async_to_sync(self.channel_layer.group_add)(
            f'person_notifications_{self.person.pk}',
            self.channel_name,
        )

        async_to_sync(self.channel_layer.group_add)(
            f'person_channel_{self.person.pk}',
            self.channel_name,
        )

        self.send_json(
            get_notifications_data(self.person)
        )

    def disconnect(self, code):
        return super().disconnect(code)

    def receive_json(self, content, **kwargs):
        message_type = content["type"]

        if message_type == "get_notifications":
            async_to_sync(self.channel_layer.group_send)(
                f'person_notifications_{self.person.pk}',
                get_notifications_data(self.person),
            )

        return super().receive_json(content, **kwargs)

    def notifications_data(self, event):
        self.send_json(event)

    def conversation_details(self, event):
        self.send_json(event)

    def conversation_delete(self, event):
        self.send_json(event)

    def user_settings(self, event):
        self.send_json(event)
