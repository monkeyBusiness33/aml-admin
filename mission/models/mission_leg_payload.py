from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from shortuuidfield import ShortUUIDField


class MissionLegPassengersPayload(models.Model):
    identifier = models.IntegerField(_("Identifier"))
    sync_id = ShortUUIDField(auto=True, editable=False)
    gender = models.ForeignKey("user.PersonGender", verbose_name=_("Gender"),
                               related_name='mission_legs_passengers_payloads',
                               on_delete=models.CASCADE)
    weight = models.IntegerField(_("Weight (lbs)"))
    note = models.CharField(_("Note"), max_length=200, null=True, blank=True)
    mission_legs = models.ManyToManyField("mission.MissionLeg", verbose_name='Mission Leg',
                                          related_name='passengers',
                                          through='MissionPassengerMissionLeg')

    class Meta:
        db_table = 'missions_legs_payload_passengers'
        app_label = 'mission'
        ordering = ['id', 'identifier']


@receiver(post_save, sender=MissionLegPassengersPayload)
def mission_leg_passengers_payload_post_save(sender, instance, created, **kwargs): # noqa
    for mission_leg in instance.mission_legs.all():
        if hasattr(mission_leg, 'turnaround') and mission_leg.turnaround.handling_request:
            arrival_sfr = mission_leg.turnaround.handling_request
            arrival_sfr.passengers_payloads.update_or_create(
                handling_request=arrival_sfr,
                sync_id=instance.sync_id,
                defaults={
                    'gender': instance.gender,
                    'weight': instance.weight,
                    'note': instance.note,
                    'is_arrival': True,
                }
            )

        if mission_leg.previous_leg and hasattr(mission_leg.previous_leg, 'turnaround') and \
                mission_leg.previous_leg.turnaround.handling_request:
            departure_sfr = mission_leg.previous_leg.turnaround.handling_request
            departure_sfr.passengers_payloads.update_or_create(
                handling_request=departure_sfr,
                sync_id=instance.sync_id,
                defaults={
                    'gender': instance.gender,
                    'weight': instance.weight,
                    'note': instance.note,
                    'is_departure': True,
                }
            )


@receiver(post_delete, sender=MissionLegPassengersPayload)
def mission_leg_passengers_payload_post_delete(sender, instance, **kwargs): # noqa
    from handling.models import HandlingRequestPassengersPayload
    HandlingRequestPassengersPayload.objects.filter(sync_id=instance.sync_id).delete()


class MissionPassengerMissionLeg(models.Model):
    mission_leg = models.ForeignKey("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                    related_name='passengers_intermediate',
                                    on_delete=models.CASCADE)
    passenger = models.ForeignKey("mission.MissionLegPassengersPayload", verbose_name=_("Crew Member"),
                                  on_delete=models.CASCADE,
                                  related_name='mission_legs_intermediate')

    class Meta:
        db_table = 'missions_passengers_flight_legs'
        app_label = 'mission'


@receiver(post_delete, sender=MissionLegPassengersPayload)
def missions_passengers_flight_legs_post_delete(sender, instance, **kwargs): # noqa
    from handling.models import HandlingRequestPassengersPayload
    HandlingRequestPassengersPayload.objects.filter(sync_id=instance.passenger.sync_id).delete()


class MissionLegCargoPayload(models.Model):
    sync_id = ShortUUIDField(auto=True, editable=False)
    description = models.CharField(_("Description"), max_length=200)
    length = models.IntegerField(_("Length"))
    width = models.IntegerField(_("Width"))
    height = models.IntegerField(_("Height"))
    weight = models.IntegerField(_("Weight (lbs)"))
    quantity = models.IntegerField(_("Quantity"))
    is_dg = models.BooleanField(_("Dangerous Goods"), default=False)
    note = models.CharField(_("Notes"), max_length=200, null=True, blank=True)
    mission_legs = models.ManyToManyField("mission.MissionLeg", verbose_name='Mission Legs',
                                          related_name='cargo',
                                          through='MissionCargoMissionLeg')

    class Meta:
        db_table = 'missions_legs_payload_cargo'
        app_label = 'mission'
        ordering = ['id']


@receiver(post_save, sender=MissionLegCargoPayload)
def mission_leg_cargo_payload_post_save(sender, instance, created, **kwargs): # noqa
    for mission_leg in instance.mission_legs.all():
        if hasattr(mission_leg, 'turnaround') and mission_leg.turnaround.handling_request:
            arrival_sfr = mission_leg.turnaround.handling_request
            arrival_sfr.cargo_payloads.update_or_create(
                handling_request=arrival_sfr,
                sync_id=instance.sync_id,
                defaults={
                    'description': instance.description,
                    'length': instance.length,
                    'width': instance.width,
                    'height': instance.height,
                    'weight': instance.weight,
                    'quantity': instance.quantity,
                    'is_dg': instance.is_dg,
                    'note': instance.note,
                    'is_arrival': True,
                }
            )

        if mission_leg.previous_leg and hasattr(mission_leg.previous_leg, 'turnaround') and \
                mission_leg.previous_leg.turnaround.handling_request:
            departure_sfr = mission_leg.previous_leg.turnaround.handling_request
            departure_sfr.cargo_payloads.update_or_create(
                handling_request=departure_sfr,
                sync_id=instance.sync_id,
                defaults={
                    'description': instance.description,
                    'length': instance.length,
                    'width': instance.width,
                    'height': instance.height,
                    'weight': instance.weight,
                    'quantity': instance.quantity,
                    'is_dg': instance.is_dg,
                    'note': instance.note,
                    'is_departure': True,
                }
            )


@receiver(post_delete, sender=MissionLegCargoPayload)
def mission_leg_cargo_payload_post_delete(sender, instance, **kwargs): # noqa
    from handling.models import HandlingRequestCargoPayload
    HandlingRequestCargoPayload.objects.filter(sync_id=instance.sync_id).delete()


class MissionCargoMissionLeg(models.Model):
    mission_leg = models.ForeignKey("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                    related_name='cargo_intermediate',
                                    on_delete=models.CASCADE)
    cargo_payload = models.ForeignKey("mission.MissionLegCargoPayload", verbose_name=_("Cargo Payload"),
                                      on_delete=models.CASCADE,
                                      related_name='mission_legs_intermediate')

    class Meta:
        db_table = 'missions_cargo_flight_legs'
        app_label = 'mission'


@receiver(post_delete, sender=MissionCargoMissionLeg)
def missions_cargo_flight_legs_post_delete(sender, instance, **kwargs): # noqa
    from handling.models import HandlingRequestCargoPayload
    HandlingRequestCargoPayload.objects.filter(sync_id=instance.cargo_payload.sync_id).delete()
