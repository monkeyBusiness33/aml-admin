from django.views.generic import TemplateView


class MissionGroundServicingUpdateMixin(TemplateView):
    template_name = 'mission_details/_modal_ground_servicing.html'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mission_id'] = self.kwargs['pk']
        return context
