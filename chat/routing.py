from django.urls import path

from chat.consumers import ChatConsumer, NotificationsConsumer

websocket_urlpatterns = [
    path("chat/ws/notifications/", NotificationsConsumer.as_asgi()),
    path("chat/ws/<slug:conversation_id>/", ChatConsumer.as_asgi()),

]
