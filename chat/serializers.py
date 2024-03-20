from django.db.models import Q
from django.urls import reverse
from rest_framework import serializers

from api.serializers.user import PersonSerializer
from chat.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    author = PersonSerializer()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'timestamp', 'author', 'content', 'is_read', 'seen_by', ]

    def get_is_read(self, obj):  # noqa
        if hasattr(obj, 'is_read_annotated'):
            return obj.is_read_annotated
        return obj.seen_by.exclude(pk=obj.author.pk).exists()


class ConversationSerializer(serializers.ModelSerializer):
    people = PersonSerializer(many=True)
    latest_message_text = serializers.SerializerMethodField()
    latest_message_timestamp = serializers.SerializerMethodField()
    unread_messages = serializers.SerializerMethodField()
    handling_request_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    is_person_participant = serializers.SerializerMethodField()
    is_deletable = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id',
                  'name',
                  'handling_request',
                  'mission',
                  'handling_request_url',
                  'is_person_participant',
                  'is_deletable',
                  'people',
                  'latest_message_text',
                  'latest_message_timestamp',
                  'unread_messages',
                  ]

    def get_name(self, obj):  # noqa
        return obj.get_name()

    def get_latest_message_text(self, obj):  # noqa
        if hasattr(obj, 'latest_message_text_val'):
            return obj.latest_message_text_val
        latest_message = obj.messages.order_by('-timestamp').first()
        return latest_message.content if latest_message else None

    def get_latest_message_timestamp(self, obj):  # noqa
        if hasattr(obj, 'latest_message_date_val'):
            return obj.latest_message_date_val

        latest_message = obj.messages.order_by('-timestamp').first()
        return latest_message.timestamp.isoformat().replace("+00:00", "Z") if latest_message else None

    def get_unread_messages(self, obj):
        if hasattr(obj, 'unread_messages_count_val'):
            return obj.unread_messages_count_val
        person = self.context["person"]
        if not obj.people.filter(pk=person.pk).exists():
            return 0
        return obj.messages.filter(
            ~Q(author=person) & ~Q(seen_by=person)
        ).count()

    def get_handling_request_url(self, obj):
        request = self.context.get('request')
        if not request:
            return None

        app_mode = self.context["request"].app_mode
        url = None
        if obj.handling_request_id:
            if app_mode == 'ops_portal':
                url = reverse('admin:handling_request', kwargs={'pk': obj.handling_request_id})
            if app_mode == 'dod_portal':
                url = reverse('dod:request', kwargs={'pk': obj.handling_request_id})
        if obj.mission_id:
            if app_mode == 'ops_portal':
                url = reverse('admin:missions_details', kwargs={'pk': obj.mission_id})
            if app_mode == 'dod_portal':
                url = reverse('dod:missions_details', kwargs={'pk': obj.mission_id})

        return url

    def get_is_person_participant(self, obj):
        if hasattr(obj, 'is_person_participant_val'):
            return obj.is_person_participant_val
        person = self.context["person"]
        return obj.people.filter(pk=person.pk).exists()

    def get_is_deletable(self, obj):
        person = self.context["person"]
        if hasattr(person, 'user'):
            if person.user.is_staff:
                return True
        return False
