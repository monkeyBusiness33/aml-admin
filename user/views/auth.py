# -*- encoding: utf-8 -*-
import logging
import warnings
import time
from inspect import signature

from django.contrib.auth.views import PasswordResetConfirmView
from django.core.signing import BadSignature
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.shortcuts import redirect, resolve_url
from django.contrib.auth import REDIRECT_FIELD_NAME, login
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView
from django_otp import devices_for_user
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from django_otp.plugins.otp_static.models import StaticDevice
from two_factor.plugins.registry import registry
from two_factor.utils import default_device

from ..forms import *

from uuid import uuid4
from two_factor import signals
from django.forms import Form, ValidationError
from two_factor.views import SetupView, OTPRequiredMixin
from two_factor.forms import BackupTokenForm, MethodForm
from two_factor.views.utils import get_remember_device_cookie, validate_remember_device_cookie, \
    IdempotentSessionWizardView, class_view_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from ..utils.redirects import get_user_landing_page

from django.contrib.auth.views import RedirectURLMixin

REMEMBER_COOKIE_PREFIX = getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_PREFIX', 'remember-cookie_')
logger = logging.getLogger(__name__)


# class AdminLoginView(LoginView):
class AdminLoginView(RedirectURLMixin, IdempotentSessionWizardView):
    """
    1:1 copy of the two_factor.views.LoginView to be able to overwrite some parts
    Changes:
    - form_list
    - get_form
    - get_success_url()
    """
    AUTH_STEP = "auth"
    TOKEN_STEP = "token"
    BACKUP_STEP = "backup"
    FIRST_STEP = AUTH_STEP

    template_name = 'users/login.html'
    form_list = (
        (AUTH_STEP, AMLAdminLoginForm),
        (TOKEN_STEP, CustomAuthenticationTokenForm),
        (BACKUP_STEP, BackupTokenForm),
    )

    redirect_authenticated_user = False
    storage_name = 'two_factor.views.utils.LoginStorage'

    def has_token_step(self):
        return (
            default_device(self.get_user()) and
            not self.remember_agent
        )

    def has_backup_step(self):
        return (
            default_device(self.get_user()) and
            self.TOKEN_STEP not in self.storage.validated_step_data and
            not self.remember_agent
        )

    @cached_property
    def expired(self):
        login_timeout = getattr(settings, 'TWO_FACTOR_LOGIN_TIMEOUT', 600)
        if login_timeout == 0:
            return False
        expiration_time = self.storage.data.get("authentication_time", 0) + login_timeout
        return int(time.time()) > expiration_time

    condition_dict = {
        TOKEN_STEP: has_token_step,
        BACKUP_STEP: has_backup_step,
    }
    redirect_field_name = REDIRECT_FIELD_NAME

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = None
        self.device_cache = None
        self.cookies_to_delete = []
        self.show_timeout_error = False

    def post(self, *args, **kwargs):
        """
        The user can select a particular device to challenge, being the backup
        devices added to the account.
        """
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)

        if wizard_goto_step == self.FIRST_STEP:
            self.storage.reset()

        if self.expired and self.step_requires_authentication(self.steps.current):
            logger.info("User's authentication flow has timed out. The user "
                        "has been redirected to the initial auth form.")
            self.storage.reset()
            self.show_timeout_error = True
            return self.render_goto_step(self.FIRST_STEP)

        # Generating a challenge doesn't require to validate the form.
        if 'challenge_device' in self.request.POST:
            self.storage.data['challenge_device'] = self.request.POST['challenge_device']
            return self.render_goto_step(self.TOKEN_STEP)

        response = super().post(*args, **kwargs)
        return self.delete_cookies_from_response(response)

    def done(self, form_list, **kwargs):
        """
        Login the user and redirect to the desired page.
        """

        # Check if remember cookie should be set after login
        current_step_data = self.storage.get_step_data(self.steps.current)
        remember = bool(current_step_data and current_step_data.get('token-remember') == 'on')

        login(self.request, self.get_user())

        redirect_to = self.get_success_url()

        device = getattr(self.get_user(), 'otp_device', None)
        response = redirect(redirect_to)

        if device:
            signals.user_verified.send(sender=__name__, request=self.request,
                                       user=self.get_user(), device=device)

            # Set a remember cookie if activated

            if getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_AGE', None) and remember:
                # choose a unique cookie key to remember devices for multiple users in the same browser
                cookie_key = REMEMBER_COOKIE_PREFIX + str(uuid4())
                cookie_value = get_remember_device_cookie(user=self.get_user(),
                                                          otp_device_id=device.persistent_id)
                response.set_cookie(cookie_key, cookie_value,
                                    max_age=settings.TWO_FACTOR_REMEMBER_COOKIE_AGE,
                                    domain=getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_DOMAIN', None),
                                    path=getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_PATH', '/'),
                                    secure=getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_SECURE', False),
                                    httponly=getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_HTTPONLY', True),
                                    samesite=getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_SAMESITE', 'Lax'),
                                    )
            return response

        # If the user does not have a device.
        elif OTPRequiredMixin.is_otp_view(self.request.GET.get('next')):
            if self.request.GET.get('next'):
                self.request.session['next'] = self.get_success_url()
            return redirect('admin:two_factor_setup')

        return response

    def get_success_url(self):
        return get_user_landing_page(self.request.user)

    # Copied from django.contrib.auth.views.LoginView (Branch: stable/1.11.x)
    # https://github.com/django/django/blob/58df8aa40fe88f753ba79e091a52f236246260b3/django/contrib/auth/views.py#L67
    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''

    def get_form_kwargs(self, step=None):
        if step is None:
            return {}

        form_class = self.get_form_list()[step]
        form_params = signature(form_class).parameters

        kwargs = {}
        if 'user' in form_params:
            kwargs['user'] = self.get_user()
        if 'initial_device' in form_params:
            kwargs['initial_device'] = self.get_device(step)
        if 'request' in form_params:
            kwargs['request'] = self.request
        return kwargs

    def get_done_form_list(self):
        """
        Return the forms that should be processed during the final step
        """
        # Intentionally do not process the auth form on the final step. We
        # haven't stored this data, and it isn't required to login the user
        form_list = self.get_form_list()
        form_list.pop(self.AUTH_STEP)
        return form_list

    def process_step(self, form):
        """
        Process an individual step in the flow
        """
        # To prevent saving any private auth data to the session store, we
        # validate the authentication form, determine the resulting user, then
        # only store the minimum needed to login that user (the user's primary
        # key and the backend used)
        if self.steps.current == self.AUTH_STEP:
            user = form.is_valid() and form.user_cache
            self.storage.reset()
            self.storage.authenticated_user = user
            self.storage.data["authentication_time"] = int(time.time())

            # By returning None when the user clicks the "back" button to the
            # auth step the form will be blank with validation warnings
            return None

        return super().process_step(form)

    def process_step_files(self, form):
        """
        Process the files submitted from a specific test
        """
        if self.steps.current == self.AUTH_STEP:
            return {}
        return super().process_step_files(form)

    def get_form(self, step=None, **kwargs):
        """
        Returns the form for the step
        """
        if (step or self.steps.current) == self.TOKEN_STEP:
            # Set form class dynamically depending on user device.
            # method = registry.method_from_device(self.get_device())
            self.form_list[self.TOKEN_STEP] = CustomAuthenticationTokenForm
        form = super().get_form(step=step, **kwargs)
        if self.show_timeout_error:
            form.cleaned_data = getattr(form, 'cleaned_data', {})
            form.add_error(None, ValidationError(_('Your session has timed out. Please login again.')))
        return form

    def get_device(self, step=None):
        """
        Returns the OTP device selected by the user, or his default device.
        """
        if not self.device_cache:
            challenge_device_id = (
                self.request.POST.get('challenge_device')
                or self.storage.data.get('challenge_device')
            )
            if challenge_device_id:
                for device in self.get_devices():
                    if device.persistent_id == challenge_device_id:
                        self.device_cache = device
                        break

            if step == self.BACKUP_STEP:
                try:
                    self.device_cache = self.get_user().staticdevice_set.get(name='backup')
                except StaticDevice.DoesNotExist:
                    pass

            if not self.device_cache:
                self.device_cache = default_device(self.get_user())

        return self.device_cache

    def get_devices(self):
        user = self.get_user()

        devices = []
        for method in registry.get_methods():
            devices += list(method.get_devices(user))
        return devices

    def get_other_devices(self, main_device):
        user = self.get_user()

        other_devices = []
        for method in registry.get_methods():
            other_devices += list(method.get_other_authentication_devices(user, main_device))

        return other_devices

    def step_requires_authentication(self, step):
        return step != self.FIRST_STEP

    def render(self, form=None, **kwargs):
        """
        If the user selected a device, ask the device to generate a challenge;
        either making a phone call or sending a text message.
        """
        if self.steps.current == self.TOKEN_STEP:
            form_with_errors = form and form.is_bound and not form.is_valid()
            if not form_with_errors:
                self.get_device().generate_challenge()
        return super().render(form, **kwargs)

    def get_user(self):
        """
        Returns the user authenticated by the AuthenticationForm. Returns False
        if not a valid user; see also issue #65.
        """
        if not self.user_cache:
            self.user_cache = self.storage.authenticated_user
        return self.user_cache

    def get_context_data(self, form, **kwargs):
        """
        Adds user's default and backup OTP devices to the context.
        """
        context = super().get_context_data(form, **kwargs)
        if self.steps.current == self.TOKEN_STEP:
            device = self.get_device()
            context['device'] = device
            context['other_devices'] = self.get_other_devices(device)

            try:
                context['backup_tokens'] = self.get_user().staticdevice_set\
                    .get(name='backup').token_set.count()
            except StaticDevice.DoesNotExist:
                context['backup_tokens'] = 0

        if getattr(settings, 'LOGOUT_REDIRECT_URL', None):
            context['cancel_url'] = resolve_url(settings.LOGOUT_REDIRECT_URL)
        elif getattr(settings, 'LOGOUT_URL', None):
            warnings.warn(
                "LOGOUT_URL has been replaced by LOGOUT_REDIRECT_URL, please "
                "review the URL and update your settings.",
                DeprecationWarning)
            context['cancel_url'] = resolve_url(settings.LOGOUT_URL)
        return context

    @cached_property
    def remember_agent(self):
        """
        Returns True if a user, browser and device is remembered using the remember cookie.
        """
        if not getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_AGE', None):
            return False

        user = self.get_user()
        devices = list(devices_for_user(user))
        for key, value in self.request.COOKIES.items():
            if key.startswith(REMEMBER_COOKIE_PREFIX) and value:
                for device in devices:
                    verify_is_allowed, extra = device.verify_is_allowed()
                    try:
                        if verify_is_allowed and validate_remember_device_cookie(
                                value,
                                user=user,
                                otp_device_id=device.persistent_id
                        ):
                            user.otp_device = device
                            device.throttle_reset()
                            return True
                    except BadSignature:
                        device.throttle_increment()
                        # Remove remember cookies with invalid signature to omit unnecessary throttling
                        self.cookies_to_delete.append(key)
        return False

    def delete_cookies_from_response(self, response):
        """
        Deletes the cookies_to_delete in the response
        """
        for cookie in self.cookies_to_delete:
            response.delete_cookie(cookie)
        return response

    # Copied from django.contrib.auth.views.LoginView  (Branch: stable/1.11.x)
    # https://github.com/django/django/blob/58df8aa40fe88f753ba79e091a52f236246260b3/django/contrib/auth/views.py#L49
    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)


class TOTPSetupView(SetupView):
    template_name = 'users/totp-setup.html'
    success_url = 'admin:two_factor_complete'
    form_list = (
        ('welcome', Form),
        ('method', MethodForm),
        ('generator', CustomTOTPDeviceForm),
    )


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class TotpSetupCompleteView(TemplateView):
    template_name = 'users/totp-setup-complete.html'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class StaffUserPasswordSetView(PasswordResetConfirmView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy("admin:staff_user_password_set_confirmation")
    form_class = SetPasswordForm


class StaffUserPasswordResetCompleteView(TemplateView):
    template_name = "users/password_change_complete.html"
