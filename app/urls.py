from django.conf import settings
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from two_factor.urls import urlpatterns as tf_urls

from core.views.base import HealthCheckView
from core.views.error_pages import error_500, error_404
import notifications.urls

from handling.views.base import HandlingLocationsSelect2View

urlpatterns = [
    path('', RedirectView.as_view(url='/ops/'), name='index'),
    path('healthcheck/', HealthCheckView.as_view(), name='healthcheck'),
    path('ops/', include('app.admin_urls')),
    path("select/", include("django_select2.urls")),
    path('api/v1/', include('api.urls', namespace='api')),
    path('api/v1/admin/', include('api.urls_admin', namespace='api_admin')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('password_reset/', RedirectView.as_view(
        url=f'https://{settings.AML_DOD_PORTAL_DOMAIN}/request_password_reset/'), name='temporary_redirect'),

    # Shared endpoints
    path('handling_locations_select2/', HandlingLocationsSelect2View.as_view(), name='handling_locations_select2'),
    re_path('^inbox/notifications/', include(notifications.urls, namespace='notifications')),
    path('', include(tf_urls)),
]

# if settings.FRONTPAGE_ENABLED:
#     urlpatterns += [
#         path('', include('frontpage.urls_frontpage', namespace='frontpage')),
#     ]

handler404 = error_404
handler500 = error_500

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
