from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django_select2.views import AutoResponseView

from handling.shared_views.handling_services import HandlingServiceSelect2Mixin
from organisation.models import Organisation, OperatorPreferredGroundHandler
from user.mixins import AdminPermissionsMixin
from user.models import Person


class HandlingServiceSelect2View(AdminPermissionsMixin, HandlingServiceSelect2Mixin):
    permission_required = ['handling.p_view']


class HandlingLocationsSelect2View(LoginRequiredMixin, AutoResponseView):
    permission_required = ['handling.p_view']

    widget = None
    term = ''
    object_list = []

    def get(self, request, *args, **kwargs):
        self.widget = self.get_widget_or_404()
        self.term = kwargs.get("term", request.GET.get("term", ""))
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse(
            {
                "results": [
                    {"text": self.widget.label_from_instance(obj),
                     "id": obj.pk,
                     "is_lat_lon_available": obj.is_lat_lon_available,
                     }
                    for obj in context["object_list"]
                ],
                "more": context["page_obj"].has_next(),
            }
        )


class HandlingRequestCreatePersonAsyncCallback(LoginRequiredMixin, View):
    """
    Json view that returns latest created Person for given organisation
    Used for the auto selection Person on the "Create HandlingRequest" page
    """

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)

        if not request.user.is_staff and not request.user.is_dod_portal_user:
            return self.handle_no_permission()

        return resp

    def get(self, request, *args, **kwargs):

        organisation = None
        if request.user.is_dod_portal_user:
            user_position = request.dod_selected_position
            organisation = user_position.organisation
        if request.user.is_staff:
            organisation_id = kwargs.get('organisation_id')
            organisation = Organisation.objects.filter(pk=organisation_id).first()

        qs = Person.objects.filter(
            organisation_people__organisation=organisation).order_by(
                '-created_at').values(
                    'id',
                    first_name=F('details__first_name'),
                    last_name=F('details__last_name')).first()
        resp = qs
        return JsonResponse(resp, safe=False)


class HandlingRequestCreateOrganisationAsyncCallback(LoginRequiredMixin, View):
    """
    Json view that returns latest created NASDL Organisation
    Used for the auto selection Location on the "Create HandlingRequest" page
    """

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)

        if not request.user.is_staff:
            return self.handle_no_permission()

        return resp

    def get(self, request, *args, **kwargs):
        qs = Organisation.objects.filter(
            details__type_id=1002,
        ).values(
            'id',
            registered_name=F('details__registered_name'),
        ).last()

        resp = qs
        return JsonResponse(resp, safe=False)


class HandlingRequestPreferredHandlerAsyncCallback(LoginRequiredMixin, View):
    """
    Json view that returns most suitable Ground Handler for the given location and organisation
    Used for the auto selection Preferred Ground Handler on the "Create HandlingRequest" page
    """
    organisation = None
    location = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['organisation_id'])
        self.location = get_object_or_404(Organisation, pk=self.kwargs['location_id'])

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)

        if not request.user.is_staff:
            if request.dod_selected_position.organisation != self.organisation:
                return self.handle_no_permission()

        return resp

    def get(self, request, *args, **kwargs):
        qs = OperatorPreferredGroundHandler.objects.filter(
            organisation_id=self.organisation,
            location_id=self.location,
        ).values(
            handler_id=F('ground_handler__pk'),
            registered_name=F('ground_handler__details__registered_name'),
        ).last()

        resp = qs
        return JsonResponse(resp, safe=False)
