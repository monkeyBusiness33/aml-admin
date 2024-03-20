from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.forms import widgets
from django.views.generic.edit import ModelFormMixin

from administration.forms._widgets import StaffRolesPickWidget
from organisation.models import OrganisationPeople
from user.models import User, PersonDetails, Person, Role
from django.core.exceptions import ValidationError
from django.conf import settings


class StaffUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'roles', ]

        widgets = {
            'username': widgets.TextInput(attrs={
                'class': 'form-control'
            }),
            'roles': StaffRolesPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        username = User.normalize_username(username)
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Username already taken')

        return username


class StaffPersonDetailsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEBUG:
            import random
            self.fields['first_name'].initial = f'Test Name {random.randint(0, 999)}'
            self.fields['last_name'].initial = f'Test Surname {random.randint(0, 999)}'
            self.fields['contact_email'].initial = f'test{random.randint(0, 9999)}@example.com'

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    def save(self, commit=True):
        person_details = super().save(commit=False)
        person = getattr(person_details, 'person', Person())
        if commit:
            if not person.pk:
                person.save()
            person_details.person = person
            person_details.save()
            person.details = person_details
            person.save()
        return person

    class Meta:
        model = PersonDetails
        fields = ['first_name', 'last_name', 'abbreviated_name',
                  'contact_email', 'contact_phone', ]
        labels = {
            'contact_email': "AML Email"
        }

        widgets = {
            'first_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'last_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'abbreviated_name': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
            'contact_email': widgets.EmailInput(attrs={
                'class': 'form-control',
            }),
            'contact_phone': widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class StaffPersonPositionForm(forms.ModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationPeople
        fields = ['job_title', ]
        widgets = {
            "job_title": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class StaffRoleForm(ModelFormMixin, BSModalModelForm):

    class Meta:
        model = Role
        fields = ['name', 'description', ]

        widgets = {
            'name': widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Role name',
            }),
            'description': widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Role description',
            }),
        }
