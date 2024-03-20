from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class HandlingRequestCrewMemberPosition(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'handling_requests_crew_positions'
        app_label = 'handling'

    def __str__(self):
        return self.name


class HandlingRequestCrew(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         related_name='mission_crew',
                                         on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", verbose_name=_("Crew Member"), on_delete=models.CASCADE,
                               related_name='sfr_crews')
    position = models.ForeignKey("handling.HandlingRequestCrewMemberPosition", verbose_name=_("Position"),
                                 default=1,
                                 on_delete=models.RESTRICT)
    is_primary_contact = models.BooleanField(_("Primary Mission Contact"), default=False)
    can_update_mission = models.BooleanField(_("Can Update Mission?"), default=False)

    class Meta:
        db_table = 'handling_requests_crew'
        app_label = 'handling'

    @property
    def person_title(self):
        position = self.person.organisation_people.filter(
            organisation=self.handling_request.customer_organisation,
        ).first()

        if position:
            return position.job_title


@receiver(post_save, sender=HandlingRequestCrew)
def handling_request_crew_post_save(sender, instance, created, **kwargs): # noqa
    """
    Generate push notification for the client user
    """
    if not hasattr(instance, 'skip_signal'):
        if created and instance.handling_request.is_standalone:
            from ..utils.client_notifications import handling_request_added_to_crew_push_notification
            handling_request_added_to_crew_push_notification.apply_async(
                kwargs={
                    'handling_request_id': instance.handling_request_id,
                    'person_id': instance.person_id,
                },
                countdown=5)
