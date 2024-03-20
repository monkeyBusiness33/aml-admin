from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django.forms import widgets, fields

from handling.form_widgets import HandlingRequestDocumentTypePickCreateWidget
from handling.models import HandlingRequestDocumentFile, HandlingRequestDocument
from django_select2 import forms as s2forms


class MissionDocumentForm(BSModalModelForm):
    applicability = fields.ChoiceField(
        label='Applicability',
        widget=s2forms.Select2Widget(attrs={
            'class': 'form-control',
        })
    )
    file = HandlingRequestDocumentFile.file.field.formfield(
        widget=widgets.FileInput(attrs={
            'class': 'form-control',
        }),
    )

    class Meta:
        model = HandlingRequestDocument
        fields = [
            'applicability',
            'type',
            'description',
            'file',
        ]
        widgets = {
            "type": HandlingRequestDocumentTypePickCreateWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "description": widgets.TextInput(attrs={
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)
        applicability_choices = [('mission', "Whole Mission")]
        self.fields['description'].required = True

        for mission_leg in self.mission.active_legs:
            applicability_choices.append(
                (f'leg_{mission_leg.pk}', f"Flight Leg {mission_leg.sequence_id} ({mission_leg.__str__()})"))
            if mission_leg.arrival_aml_service and mission_leg.turnaround and mission_leg.turnaround.handling_request:
                applicability_choices.append(
                    (f'sfr_{mission_leg.turnaround.handling_request.pk}', f"{mission_leg.turnaround.full_repr}"))

        self.fields['applicability'].choices = applicability_choices

    def save(self, commit=True):
        document = super().save(commit=False)
        applicability = self.cleaned_data['applicability']

        if applicability == 'mission':
            document.mission = self.mission
        else:
            applicability, applicability_id = applicability.split('_')
            if applicability == 'leg':
                document.mission_leg = self.mission.active_legs.get(pk=applicability_id)
            elif applicability == 'sfr':
                document.handling_request = self.mission.handling_requests.get(pk=applicability_id)

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            if commit:
                document.save()

                document_file = HandlingRequestDocumentFile()
                document_file.document = document
                document_file.file = self.cleaned_data['file']
                document_file.uploaded_by = self.request.user.person
                document_file.save()
                self._save_m2m()

        return document
