from django import forms
from django.db.models import OuterRef, Subquery

from core.utils.datatables_functions import get_datatable_clipped_value
from handling.models import HandlingRequestDocument, HandlingRequestDocumentFile


class MissionPacketPdfForm(forms.Form):
    mission_documents = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
    )

    flight_legs_documents = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
    )

    turnaround_documents = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)

        recent_file_qs = HandlingRequestDocumentFile.objects.filter(
            document_id=OuterRef('pk')).values('file')

        documents_qs = HandlingRequestDocument.objects.annotate(
            recent_file_ext=Subquery(recent_file_qs[:1]),
        ).filter(
            recent_file_ext__iendswith='.pdf',
        )

        mission_documents_qs = documents_qs.filter(mission=self.mission)
        flight_legs_documents_qs = documents_qs.filter(mission_leg__in=self.mission.active_legs)
        turnaround_documents_qs = documents_qs.filter(handling_request__in=self.mission.handling_requests)

        self.fields['mission_documents'].choices = []
        for document in mission_documents_qs:
            self.fields['mission_documents'].choices.append((document.pk, document))

        self.fields['flight_legs_documents'].choices = []
        for document in flight_legs_documents_qs:
            self.fields['flight_legs_documents'].choices.append((document.pk, document))

        self.fields['turnaround_documents'].choices = []
        for document in turnaround_documents_qs:
            if not document.description or document.description == '':
                description = f'(No Description) [{document.recent_file.file.name}]'
            else:
                description = document.description

            description_html = get_datatable_clipped_value(text=description, max_length=50)
            self.fields['turnaround_documents'].choices.append((document.pk, description_html))
