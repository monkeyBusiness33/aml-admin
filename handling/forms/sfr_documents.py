from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django.forms import widgets

from handling.form_widgets import HandlingRequestDocumentTypePickCreateWidget
from handling.models import HandlingRequestDocumentFile, HandlingRequestDocument


class HandlingRequestDocumentForm(BSModalModelForm):
    file = HandlingRequestDocumentFile.file.field.formfield(
        widget=widgets.FileInput(attrs={
            'class': 'form-control',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = True

    class Meta:
        model = HandlingRequestDocument
        fields = ['type',
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

    def save(self, commit=True):
        document = super().save(commit=False)

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
