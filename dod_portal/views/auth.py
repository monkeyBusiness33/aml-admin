from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordResetConfirmView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from ..forms import *


class DodLoginView(LoginView):
    template_name = 'dod/user/login.html'
    form_class = DodLoginForm


class PasswordResetView(FormView):
    template_name = 'dod/user/password_reset_request.html'
    form_class = PasswordResetForm
    success_url = reverse_lazy("dod:request_password_reset_complete")
    
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class PasswordResetRequestCompleteView(TemplateView):
    template_name = "dod/user/password_reset_request_complete.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'dod/user/password_change.html'
    success_url = reverse_lazy("dod:password_reset_complete")
    form_class = SetPasswordForm


class PasswordResetCompleteView(TemplateView):
    template_name = "dod/user/password_reset_complete.html"

