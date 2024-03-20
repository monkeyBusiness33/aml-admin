from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from chat.consumers import send_conversation_details_update
from chat.models import Message, Conversation
from core.tasks import send_push
from user.models import User

channel_layer = get_channel_layer()


@receiver(post_save, sender=Message)
def conversation_message_post_save(sender, instance, created, **kwargs): # noqa
    from chat.serializers import MessageSerializer
    from chat.consumers import send_conversation_details_update
    if created and not hasattr(instance, 'skip_signal'):

        # Send message into the channels group
        async_to_sync(channel_layer.group_send)(
            instance.conversation.pk,
            {
                "type": "chat_message",
                "message": MessageSerializer(instance).data,
            }
        )
        # Send conversation update for all involved users
        send_conversation_details_update(channel_layer=channel_layer,
                                         conversation=instance.conversation,
                                         people=instance.conversation.people.all())

        # Send push notifications to conversation participants
        users_to_notify = User.objects.filter(
            person__chat_conversations=instance.conversation,
            person__chat_online__isnull=True,
        ).exclude(
            person=instance.author,
        ).values_list('id', flat=True)

        send_push.delay(
            f'DoD Comms: {instance.conversation.get_name()}',
            f'{instance.author.fullname}: {instance.content}',
            {
                'conversation_id': str(instance.conversation_id),
                'handling_request_id': str(instance.conversation.handling_request_id),
            },
            list(users_to_notify)
        )


@receiver(post_save, sender=Conversation)
def conversation_post_save(sender, instance, created, **kwargs): # noqa
    if created and not hasattr(instance, 'skip_signal'):
        for person in instance.people.all():
            send_conversation_details_update(channel_layer, instance, person)
