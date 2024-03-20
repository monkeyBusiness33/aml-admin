from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, DateField, Case, When, OuterRef, Exists
from django.forms import BaseModelFormSet, ValidationError, modelformset_factory
from bootstrap_modal_forms.mixins import PopRequestMixin
from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from crm.form_widgets import CrmActivityPickWidget
from django import forms
from django.forms import widgets
from .models import *


class OrganisationPeopleActivityForm(PopRequestMixin, forms.ModelForm):

    datetime_local = OrganisationPeopleActivity.datetime.field.formfield(
        required=True,
        widget=widgets.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
    )

    class Meta:
        model = OrganisationPeopleActivity
        fields = ['datetime', 'crm_activity', 'description', ]

        widgets = {
            "datetime": widgets.HiddenInput(attrs={
            }),
            "crm_activity": CrmActivityPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "description": widgets.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
        }


class OrganisationPeopleActivityAttachmentForm(forms.ModelForm):

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = OrganisationPeopleActivityAttachment
        fields = ['file', 'description', ]
        widgets = {
            "file": widgets.FileInput(attrs={
                'class': 'form-control',
            }),
            "description": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class OrganisationPeopleActivityAttachmentBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.activity = kwargs.pop('activity', None)
        super().__init__(*args, **kwargs)
        if self.activity:
            self.queryset = OrganisationPeopleActivityAttachment.objects.filter(
                activity=self.activity).all()
        else:
            self.queryset = OrganisationPeopleActivityAttachment.objects.none()


OrganisationPeopleActivityAttachmentFormSet = modelformset_factory(
    OrganisationPeopleActivityAttachment,
    extra=20,
    can_delete=True,
    form=OrganisationPeopleActivityAttachmentForm,
    formset=OrganisationPeopleActivityAttachmentBaseFormSet,
    fields=['file', 'description', ]
)
