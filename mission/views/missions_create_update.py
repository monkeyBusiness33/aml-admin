from django.views.generic import TemplateView

from mission.models import Mission
from user.mixins import AdminPermissionsMixin


class MissionCreateUpdateView(AdminPermissionsMixin, TemplateView):
    template_name = 'mission_create_update.html'
    permission_required = ['handling.p_create']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        mission_id = self.kwargs.get('pk')
        context['mission'] = Mission.objects.filter(pk=mission_id).first()
        return context
