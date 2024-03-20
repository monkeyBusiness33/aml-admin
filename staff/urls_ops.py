from django.urls import path
from staff.views.team_availability import *
from api.urls import urlpatterns as api_urlpatterns
from .urls_api import router
# from .urls_api import urlpatterns as staff_api_urlpatterns

urlpatterns = [
    path('team/calendar', CalendarView.as_view(), name='team_calendar'),
    path('team/schedule', ScheduleListView.as_view(), name='team_schedule')
]

# Might be wiser to move this to api/urls? or at least append there
api_urlpatterns += router.urls
# api_urlpatterns += staff_api_urlpatterns
