from rest_framework.routers import DefaultRouter, SimpleRouter

from organisation.views_api.organisations import OrganisationsViewSet

router = SimpleRouter()
router.register("", OrganisationsViewSet)

app_name = 'organisations'
urlpatterns = router.urls
