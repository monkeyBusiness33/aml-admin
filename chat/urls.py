from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from chat.views import MessageViewSet, ConversationViewSet, MetaInformationViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    class OptionalSlashRouter(SimpleRouter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.trailing_slash = '/?'
    router = OptionalSlashRouter()

router.register("conversations", ConversationViewSet)
router.register("messages", MessageViewSet)
router.register("meta", MetaInformationViewSet, basename='meta')

app_name = 'chat'
urlpatterns = router.urls
