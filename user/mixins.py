from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http.response import HttpResponse
from two_factor.views.mixins import OTPRequiredMixin
from django.contrib import messages
from bootstrap_modal_forms.mixins import is_ajax


class AdminPermissionsMixin(LoginRequiredMixin, OTPRequiredMixin, PermissionRequiredMixin):
    """
    Verify that the current user:
        - Logged in
        - Have staff permissions
        - OTP verified (OTPRequiredMixin)
        - Check permissions via Django's PermissionRequiredMixin
    """
    login_url = 'admin:login'
    verification_url = 'admin:login'
    person = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.person = getattr(request.user, 'person', None)

    def dispatch(self, request, *args, **kwargs):
        """
        This part to handle un-authenticated ajax calls in the previously
        opened browser tabs to returns empty http response to prevent
        OTP auth session being expired.
        """
        if is_ajax(request.META) and not request.user.is_verified():
            return HttpResponse()

        if not request.user.is_staff:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def get_permission_denied_message(self):
        return messages.warning(self.request, 'No Permissions')
