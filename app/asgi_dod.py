import os

from channels.auth import AuthMiddlewareStack

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings_dod')
django_asgi_app = get_asgi_application()

from chat.middleware import TokenAuthMiddleware  # noqa isort:skip
from chat import routing  # noqa isort:skip

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(TokenAuthMiddleware(URLRouter(routing.websocket_urlpatterns))),
    }
)
