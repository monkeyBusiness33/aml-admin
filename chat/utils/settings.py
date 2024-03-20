from asgiref.sync import async_to_sync

from api.serializers.user import UserSettingsSerializer
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


def send_updated_user_settings(person):
    async_to_sync(channel_layer.group_send)(
        f'person_channel_{person.pk}',
        {
            "type": "user_settings",
            "settings": UserSettingsSerializer(person.user.settings).data,
        },
    )
