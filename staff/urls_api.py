
from staff.views_api.team_availability import *
from django.conf import settings
from rest_framework.routers import SimpleRouter
from django.urls import path

class OptionalSlashRouter(SimpleRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '/?'


router = OptionalSlashRouter()
router.register("staff/calendar", PeopleEntriesViewSet, basename='calendar')
router.register("staff/calendar/specific_entries", SpecificEntryViewSet, basename='specific_entries')
router.register("staff/calendar/blanket_entries", BlanketEntryViewSet, basename='blanket_entries')
# router.register("staff/calendar/blanket_entry_overrides", BlanketEntryOverrideViewSet, basename='blanket_entry_overrides')
