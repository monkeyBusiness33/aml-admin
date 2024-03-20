from django.forms import widgets
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from dod_portal.utils.dod_user_utils import reset_dod_user_password
from handling.models import HandlingRequestServices
from user.models.user import User
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm


class DodLoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))


class PasswordResetForm(forms.Form):
    username = forms.CharField(
        label=_("Username"),
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control"
            }
        ))

    def save(self):
        username = self.cleaned_data["username"]
        user = User.objects.filter(username=username).first()
        if user:
            reset_dod_user_password(user)


class SetPasswordForm(forms.Form):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    error_messages = {
        'password_mismatch': ("The two password fields didn't match."),
    }
    new_password1 = forms.CharField(
        label=("New password"),
        required=True,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 
                   'placeholder': 'New password'}),
        )
    
    new_password2 = forms.CharField(
        label=("New password confirmation"), 
        required=True,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 
                   'placeholder': 'Password confirmation'}),
        )

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class HandlingServiceInternalNoteForm(BSModalModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = HandlingRequestServices
        fields = ['note', ]
        widgets = {
            "note": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
        }
