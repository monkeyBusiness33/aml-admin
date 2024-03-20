from django.http import HttpResponse, JsonResponse
from django.views import View
from django_select2.views import AutoResponseView

from ..mixins import DodPermissionsMixin
from django.views.generic.base import TemplateView


class DummyJsonResponse(DodPermissionsMixin, View):
    """
    Dummy json response that always return success:true
    Added due to async bootstrap-modal requires response to
    complete form submit.
    """

    def get(self, request, *args, **kwargs):
        resp = dict()
        resp['table'] = {'success': 'true'}
        return JsonResponse(resp)


class SetCurrentOrganisationView(DodPermissionsMixin, View):

    def post(self, request):
        position_id = request.POST.get('position_id', None)
        if position_id:
            request.session['dod_selected_position'] = position_id

        return HttpResponse('ok')


class PlannersPortalTermsAndConditions(DodPermissionsMixin, TemplateView):
    template_name = 'dod/terms_and_conditions.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'AML DoD Terms & Conditions',
        }

        context['metacontext'] = metacontext
        return context


class AuthenticatedSelect2View(DodPermissionsMixin, AutoResponseView):
    pass
