from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponse, Http404
from django.contrib import messages
from bootstrap_modal_forms.mixins import is_ajax

from handling.models import HandlingRequest


class DodPermissionsMixin(LoginRequiredMixin):
    """
    Verify that the current user:
        - Logged in
        - Is DoD Portal User
    """
    person_position = None
    person = None
    login_url = 'dod:login'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.person = getattr(request.user, 'person', None)
        self.person_position = getattr(request, 'dod_selected_position', None)

    def has_permission(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        """
        This part to handle unauthenticated ajax calls in the previously
        opened browser tabs to returns empty http response to prevent
        OTP auth session being expired.
        """
        if is_ajax(request.META) and not request.user.is_authenticated:
            return HttpResponse()

        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_dod_portal_user:
            return self.handle_no_permission()

        if not self.has_permission():
            return self.handle_no_permission()

        # Check specific permissions if it applicable
        permission_required = getattr(self, 'permission_required', None)
        if permission_required:
            user_perms = request.dod_selected_position.applications_access.values_list(
                'code', flat=True)
            has_perm = set(permission_required).intersection(user_perms)
            if not has_perm:
                return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def get_permission_denied_message(self):
        return messages.warning(self.request, 'No Permissions')


class GetHandlingRequestMixin:
    """
    Mixing helps to pull HandlingRequest instance from the database by 'handling_request_id' or 'pk' url kwarg
    """
    handling_request = None
    missions_filer_owned = None
    missions_filer_managed = None

    def __init__(self):
        self.kwargs = None

    def get_queryset(self):
        user_position = getattr(self.request, 'dod_selected_position')
        return user_position.managed_sfr_list

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        handling_request_id = self.kwargs.get('handling_request_id')
        if not handling_request_id:
            handling_request_id = self.kwargs['pk']

        user_position = getattr(request, 'dod_selected_position')
        missions = user_position.get_sfr_list(managed=self.missions_filer_managed, owned=self.missions_filer_owned)

        try:
            self.handling_request = missions.get(pk=handling_request_id)
        except HandlingRequest.DoesNotExist:
            raise Http404
