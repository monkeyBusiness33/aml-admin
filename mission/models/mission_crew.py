from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class MissionCrewPosition(models.Model):
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                related_name='mission_crew_positions',
                                on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", verbose_name=_("Crew Member"), on_delete=models.CASCADE,
                               related_name='mission_crew_positions')
    position = models.ForeignKey("handling.HandlingRequestCrewMemberPosition", verbose_name=_("Position"),
                                 default=1,
                                 on_delete=models.RESTRICT)
    is_primary_contact = models.BooleanField(_("Primary Mission Contact"), default=False)
    can_update_mission = models.BooleanField(_("Can Update Mission?"), default=False)
    legs = models.ManyToManyField("mission.MissionLeg", verbose_name='Mission Leg',
                                  related_name='crew_positions',
                                  through='MissionCrewPositionLeg')

    class Meta:
        db_table = 'missions_crew_people'
        app_label = 'mission'


@receiver(post_save, sender=MissionCrewPosition)
def mission_crew_position_post_save(sender, instance, created, **kwargs): # noqa
    if hasattr(instance, 'skip_signal'):
        return None
    if created and hasattr(instance, 'updated_by'):
        instance.mission.activity_log.create(
            record_slug='mission_crew_position_create',
            details=f'{instance.person.fullname} added to the mission crew',
            author=getattr(instance, 'updated_by'),
        )


@receiver(pre_delete, sender=MissionCrewPosition)
def mission_crew_position_pre_delete(sender, instance, **kwargs): # noqa
    instance.mission.activity_log.create(
        record_slug='mission_crew_position_delete',
        details=f'{instance.person.fullname} removed from the mission crew.',
        author=getattr(instance, 'updated_by', None),
    )


class MissionCrewPositionLeg(models.Model):
    mission_leg = models.ForeignKey("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                    related_name='crew',
                                    on_delete=models.CASCADE)
    crew_position = models.ForeignKey("mission.MissionCrewPosition", verbose_name=_("Crew Member"),
                                      on_delete=models.CASCADE,
                                      related_name='mission_legs_crew')

    class Meta:
        db_table = 'missions_crew_legs'
        app_label = 'mission'
