from django.contrib.auth.validators import UnicodeUsernameValidator
from core.form_widgets import AmlApplicationsPickWidget, TagPickCreateWidget, CountryPickWidget
from core.forms import ClearableMultipleFileInput
from organisation.form_widgets import OrganisationPersonRolePickWidget, OrganisationPickWidget
from organisation.models.organisation_people import OrganisationPeople
from .models import TravelDocument
from .models.user import User
from .models.person import Person, PersonDetails
from .form_widgets import PersonPositionAircraftTypesPickWidget, PersonPronounPickWidget, PersonTitlePickWidget
from django import forms
from django.forms import BaseModelFormSet, modelformset_factory, widgets
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from two_factor.forms import TOTPDeviceForm, AuthenticationTokenForm
from two_factor.utils import totp_digits
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax


class AMLAdminLoginForm(AuthenticationForm):

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

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )
        if not user.is_staff:
            raise ValidationError(
                'Login not permitted',
                code='invalid_login',
            )


class SetPasswordForm(forms.Form):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    error_messages = {
        'password_mismatch': "The two password fields didn't match.",
    }
    new_password1 = forms.CharField(
        label="New password",
        required=True,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control',
                   'placeholder': 'New password'}),
    )

    new_password2 = forms.CharField(
        label="New password confirmation",
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


class CustomTOTPDeviceForm(TOTPDeviceForm):
    token = forms.IntegerField(
        label=_("Token"),
        min_value=0,
        max_value=int('9' * totp_digits()),
        widget=forms.TextInput(
            attrs={
                'placeholder': "OTP code",
                'class': 'form-control',
                'autofocus': 'autofocus',
                'autocomplete': 'one-time-code'
            }
        )
    )


class CustomAuthenticationTokenForm(AuthenticationTokenForm):
    otp_token = forms.RegexField(label=_("Token"),
                                 regex=r'^[0-9]*$',
                                 min_length=totp_digits(),
                                 max_length=totp_digits())
    otp_token.widget.attrs.update({
        'placeholder': 'OTP code',
        'class': 'form-control',
        'autofocus': 'autofocus',
        'pattern': '[0-9]*',  # hint to show numeric keyboard for on-screen keyboards
        'autocomplete': 'one-time-code',
    })


class PersonTagsForm(BSModalModelForm):

    class Meta:
        model = Person
        fields = ['tags', ]
        widgets = {
            "tags": TagPickCreateWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class PersonDetailsForm(forms.ModelForm):

    username_validator = UnicodeUsernameValidator()
    username = User.username.field.formfield(
        label='Username (for AML Application Access)',
        required=False,
        validators=[username_validator],
        widget=forms.TextInput(
            attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].empty_label = 'Pick Person Title'
        self.fields['personal_pronoun'].empty_label = 'Pick Person Personal Pronoun'

        if hasattr(self.instance, 'person'):
            if hasattr(self.instance.person, 'user'):
                self.fields['username'].initial = self.instance.person.user.username
                self.fields['username'].disabled = True

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def clean_username(self):
        username = self.cleaned_data['username']
        username = User.normalize_username(username)
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already taken')

        return username

    class Meta:
        model = PersonDetails
        fields = ['first_name', 'middle_name', 'last_name',
                  'title', 'abbreviated_name', 'personal_pronoun',
                  'contact_email', 'contact_phone', ]

        widgets = {
            "first_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "middle_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "last_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "title": PersonTitlePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "abbreviated_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "personal_pronoun": PersonPronounPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "contact_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class PersonPositionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'organisation'):
            self.fields['organisation'].disabled = True

        if not self.request.user.has_perm('core.p_contacts_person_app_access_add'):
            self.fields['applications_access'].disabled = True

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationPeople
        fields = ['organisation', 'job_title', 'role',
                  'contact_email', 'contact_phone', 'start_date',
                  'is_decision_maker', 'aircraft_types', 'applications_access', ]
        labels = {
            'start_date': _('Start Date (if known)'),
        }
        widgets = {
            "organisation": OrganisationPickWidget(attrs={
                'class': 'form-control'
            }),
            "job_title": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "role": OrganisationPersonRolePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "contact_email": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "start_date": widgets.DateInput(attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }),
            "is_decision_maker": widgets.CheckboxInput(attrs={
                'class': 'form-check-input d-block',
            }),
            "aircraft_types": PersonPositionAircraftTypesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "applications_access": AmlApplicationsPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }


class PersonPositionBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.person = kwargs.pop('person', None)
        super().__init__(*args, **kwargs)
        if self.person:
            self.queryset = OrganisationPeople.objects.filter(
                person=self.person).all()
        else:
            self.queryset = OrganisationPeople.objects.none()
        self.forms[0].empty_permitted = False
        for field in self.forms[0].fields:
            field_required_flag = self.forms[0].fields[field].required
            if field_required_flag == True:
                self.forms[0].fields[field].widget.attrs['required'] = 'required'

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['request'] = self.request
        return kwargs


PersonPositionFormSet = modelformset_factory(
    OrganisationPeople,
    extra=4,
    can_delete=True,
    form=PersonPositionForm,
    formset=PersonPositionBaseFormSet,
    fields=['organisation', 'job_title', 'role',
            'contact_email', 'contact_phone', 'start_date',
            'is_decision_maker', 'aircraft_types', 'applications_access', ]
)


class TravelDocumentForm(BSModalModelForm):
    files = forms.FileField(
        label='File(s)',
        required=False,
        widget=ClearableMultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
        }),
    )

    class Meta:
        model = TravelDocument
        fields = ['type', 'number', 'issue_country', 'start_date', 'end_date',
                  'dob', 'nationality', 'comments', 'files', ]
        widgets = {
            "type": CountryPickWidget(attrs={
                'class': 'form-control',
            }),
            "number": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "issue_country": CountryPickWidget(attrs={
                'class': 'form-control',
            }),
            "start_date": widgets.DateInput(attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }),
            "end_date": widgets.DateInput(attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }),
            "dob": widgets.DateInput(attrs={
                'class': 'form-control',
                'data-datepicker': '',
            }),
            "nationality": CountryPickWidget(attrs={
                'class': 'form-control',
            }),
            "is_current": widgets.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            "comments": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['files'].label = 'Append Files'

        if self.instance.type:
            self.fields['type'].disabled = True

    def save(self, commit=True):
        document = super().save(commit=False)

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            document.save()
            if commit:
                for file in self.request.FILES.getlist('files'):
                    document.files.create(
                        file=file,
                    )
        return document


class StaffUserOnboardingPersonDetailsForm(forms.ModelForm):

    class Meta:
        model = PersonDetails
        fields = ['first_name', 'middle_name', 'last_name',
                  'title', 'abbreviated_name',
                  'contact_email', 'contact_phone', ]
        labels = {
            'contact_email': "AML Email"
        }

        widgets = {
            "first_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "middle_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "last_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "title": PersonTitlePickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "abbreviated_name": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            "contact_email": widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            "contact_phone": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class StaffUserOnboardingPersonPositionForm(forms.ModelForm):

    class Meta:
        model = OrganisationPeople
        fields = ['job_title', ]
        widgets = {
            "job_title": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }
