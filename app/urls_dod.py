from django.urls import path, include, re_path
from django.conf import settings

import notifications.urls

from handling.views.base import HandlingLocationsSelect2View

urlpatterns = [
    path('', include('dod_portal.urls', namespace='dod')),
    path('ops/', include('app.admin_urls', namespace='admin')),  # Added for ability to use reverse()
    path('chat/', include('chat.urls', namespace='chat')),
    path('api/v1/', include('api.urls', namespace='api')),
    path("select/", include("django_select2.urls")),
    path('handling_locations_select2/', HandlingLocationsSelect2View.as_view(), name='handling_locations_select2'),
    re_path('^inbox/notifications/', include(notifications.urls, namespace='notifications')),
]

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
