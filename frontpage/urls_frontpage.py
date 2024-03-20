from django.urls import path
from .views import IndexView
from django.conf.urls.static import static
from django.conf import settings

app_name = 'frontpage'

urlpatterns = [
    path('', IndexView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
