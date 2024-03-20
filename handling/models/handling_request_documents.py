from datetime import timedelta, datetime

from celery import shared_task
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from app.storage_backends import HandlingRequestDocumentFilesStorage
from handling.utils.document_signing import signable_invoice_chase_push_notification, \
    signable_invoice_chase_email_notification, signable_invoice_uploaded_push_notification
from mission.utils.notifications_staff import notifications_staff_mission_document_uploaded


class HandlingRequestDocumentType(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'handling_requests_documents_types'
        app_label = 'handling'

    def __str__(self):
        return self.name


class HandlingRequestDocument(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         null=True, blank=True,
                                         related_name='documents',
                                         on_delete=models.CASCADE)
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                null=True, blank=True,
                                related_name='documents',
                                on_delete=models.CASCADE)
    mission_leg = models.ForeignKey("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                    null=True, blank=True,
                                    related_name='documents',
                                    on_delete=models.CASCADE)
    type = models.ForeignKey("handling.HandlingRequestDocumentType", verbose_name=_("Type"),
                             related_name='documents',
                             on_delete=models.CASCADE)
    description = models.CharField(_("Description"), max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(_("Uploaded At"), auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Uploaded By"),
                                   related_name='handling_requests_documents',
                                   null=True,
                                   on_delete=models.CASCADE)
    is_staff_added = models.BooleanField(_("Is Staff Document?"), default=True)
    is_dod_viewable = models.BooleanField(_("Is DoD Viewable?"), default=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'handling_requests_documents'
        app_label = 'handling'

    def __str__(self):
        return self.description or ''

    def save(self, *args, **kwargs):
        if not self.pk:
            # Hide documents with type 4 for Planners Portal
            if self.type_id in [4, 14]:
                self.is_dod_viewable = False

        super().save(*args, **kwargs)

    def mission_invoice_notification_people(self):
        if self.handling_request:
            # Pick 'is_primary_contact=True' with position 'Flight Crew'
            qs = self.handling_request.mission_crew.filter(
                is_primary_contact=True,
                position__name='Flight Crew'
            )

            # In case if primary contact is not 'Flight Crew' pick all 'Flight Crew' people
            if not qs:
                qs = self.handling_request.mission_crew.filter(
                    position__name='Flight Crew'
                )
            return qs

    @property
    def recent_file(self):
        recent_file = self.files.filter(is_recent=True).last()
        return recent_file

    @property
    def recent_file_download_url(self):
        recent_file = self.files.filter(is_recent=True).last()
        if recent_file and recent_file.file:
            return recent_file.file.url

    @property
    def is_signed(self):
        return self.recent_file.is_signed

    @property
    def applicability(self):
        if self.handling_request_id and hasattr(self.handling_request, 'mission_turnaround'):
            turnaround = self.handling_request.mission_turnaround
            return 'Turnaround - {location} (Legs {leg_1}&{leg_2})'.format(
                location=turnaround.mission_leg.arrival_location.tiny_repr,
                leg_1=turnaround.mission_leg.sequence_id,
                leg_2=turnaround.mission_leg.next_leg.sequence_id,
            )
        elif self.mission_leg_id:
            return 'Leg {sequence_id} ({departure_location} > {arrival_location})'.format(
                sequence_id=self.mission_leg.sequence_id,
                departure_location=self.mission_leg.departure_location.tiny_repr,
                arrival_location=self.mission_leg.arrival_location.tiny_repr,
            )
        elif self.mission_id:
            return 'Whole Mission'
        return ''

    @property
    def document_mission(self):
        if self.handling_request_id and hasattr(self.handling_request, 'mission_turnaround'):
            return self.handling_request.mission_turnaround.mission_leg.mission
        elif self.mission_leg_id:
            return self.mission_leg.mission
        elif self.mission_id:
            return self.mission
        return None


@shared_task
def signable_invoice_chase_notification_task(document_id):
    document = HandlingRequestDocument.objects.filter(pk=document_id).first()
    signable_invoice_chase_push_notification(document)
    signable_invoice_chase_email_notification(document)


@receiver(post_save, sender=HandlingRequestDocument)
def handling_request_document_post_save_actions(sender, instance, created, **kwargs): # noqa

    # Send notification on uploading mission related document
    if created and instance.document_mission:
        notifications_staff_mission_document_uploaded.apply_async(args=(instance.pk,), countdown=4)

    if created and instance.type_id == 10:
        # Send push invoice signing request notification to the SFR crew
        signable_invoice_uploaded_push_notification(instance)
        # Delay "Chase Signature" notification
        signable_invoice_chase_notification_task.apply_async(args=(instance.pk,),
                                                             eta=datetime.now() + timedelta(hours=2))


class HandlingRequestDocumentFile(models.Model):
    document = models.ForeignKey("handling.HandlingRequestDocument",
                                 verbose_name=_("Document"),
                                 related_name='files',
                                 on_delete=models.CASCADE)
    file = models.FileField(_("File"), storage=HandlingRequestDocumentFilesStorage())
    uploaded_at = models.DateTimeField(_("Uploaded At"), auto_now=False, auto_now_add=True)
    uploaded_by = models.ForeignKey("user.Person", verbose_name=_("Uploaded By"),
                                    related_name='handling_requests_document_files',
                                    null=True,
                                    on_delete=models.CASCADE)
    is_recent = models.BooleanField(_("Is File Recent?"), default=True)
    is_signed = models.BooleanField(_("Is Signed?"), null=True, blank=True, default=None)
    signed_by = models.ForeignKey("user.Person", verbose_name=_("Person"),
                                  null=True, blank=True,
                                  related_name='handling_request_document_files',
                                  on_delete=models.CASCADE)
    signed_at = models.DateTimeField(_("Signed At"), auto_now=False, auto_now_add=False, null=True)

    class Meta:
        db_table = 'handling_requests_documents_files'
        app_label = 'handling'

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.document.type_id == 10:
                self.is_signed = False

        super().save(*args, **kwargs)
        if self.pk:
            self.document.files.exclude(pk=self.pk).update(is_recent=False)
