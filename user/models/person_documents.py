from django.db import models
from django.utils.translation import gettext_lazy as _

from datetime import datetime

from app.storage_backends import TravelDocumentFilesStorage
from core.utils.datatables_functions import get_datatable_actions_button


class PeopleDocumentType(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    is_td = models.BooleanField(_("Is TD?"), default=False)

    class Meta:
        db_table = 'people_documents_types'

    def __str__(self):
        return self.name


class TravelDocument(models.Model):
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='travel_documents',
                               on_delete=models.CASCADE)
    type = models.ForeignKey("user.PeopleDocumentType", verbose_name=_("Type"),
                             related_name='travel_documents',
                             on_delete=models.CASCADE)
    number = models.CharField(_("Document Number"), max_length=100, null=True, blank=True)
    issue_country = models.ForeignKey("core.Country", verbose_name=_("Issue Country"),
                                      related_name='travel_documents_issue_country',
                                      null=True, blank=True,
                                      on_delete=models.SET_NULL)
    start_date = models.DateField(_("Start Date"), null=True, blank=True)
    end_date = models.DateField(_("End Date"), null=True, blank=True)
    dob = models.DateField(_("Dob"), null=True, blank=True)
    nationality = models.ForeignKey("core.Country", verbose_name=_("Nationality"),
                                    related_name='travel_documents_nationality',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    is_current = models.BooleanField(_("Is Current?"), default=False)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   related_name='updated_travel_documents',
                                   null=True, blank=True,
                                   on_delete=models.CASCADE)

    class Meta:
        db_table = 'people_documents'

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.is_valid:
                self.is_current = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.person_id}'

    @property
    def is_valid(self):
        if not self.start_date or not self.end_date:
            return False
        if self.start_date <= datetime.now().date() <= self.end_date:
            return True
        return False

    def get_files_download_icons(self):
        document_files = []
        for document_file in self.files.all():
            btn = get_datatable_actions_button(button_text='',
                                               button_url=document_file.file.url,
                                               button_class='fa-file-download',
                                               button_active=True,
                                               button_popup=f'Download {document_file.file.name}',
                                               button_modal=False,
                                               modal_validation=False)
            document_files.append(btn)
        document_files_html = ''.join(map(str, document_files))
        return document_files_html


class TravelDocumentFile(models.Model):
    travel_document = models.ForeignKey("user.TravelDocument", verbose_name=_("Travel Document"),
                                        related_name='files',
                                        on_delete=models.CASCADE)
    file = models.FileField(_("File"), storage=TravelDocumentFilesStorage())

    class Meta:
        db_table = 'people_documents_files'

    def __str__(self):
        return f'{self.pk}'
