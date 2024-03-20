import shortuuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from shortuuidfield import ShortUUIDField


class HandlingRequestPassengersPayload(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Passengers Payload"),
                                         related_name='passengers_payloads',
                                         on_delete=models.CASCADE)
    identifier = models.IntegerField(_("Identifier"))
    sync_id = ShortUUIDField(auto=True, editable=False)
    gender = models.ForeignKey("user.PersonGender", verbose_name=_("Gender"),
                               related_name='handling_request_passenger_payloads',
                               on_delete=models.CASCADE)
    weight = models.IntegerField(_("Weight (lbs)"))
    note = models.CharField(_("Note"), max_length=200, null=True, blank=True)
    is_arrival = models.BooleanField(_("Arriving"), default=False)
    is_departure = models.BooleanField(_("Departing"), default=False)

    class Meta:
        db_table = 'handling_requests_payloads_passengers'
        app_label = 'handling'
        ordering = ['identifier']

    def save(self, *args, **kwargs):
        # Assign auto-incrementing identifier for Mission sourced rows
        if not self.identifier:
            highest_identifier = self.handling_request.passengers_payloads.order_by(
                'identifier').values('identifier').last()
            self.identifier = highest_identifier['identifier'] + 1 if highest_identifier else 1
        super().save(*args, **kwargs)


class HandlingRequestCargoPayload(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         related_name='cargo_payloads',
                                         on_delete=models.CASCADE)
    sync_id = ShortUUIDField(auto=True, editable=False)
    description = models.CharField(_("Description"), max_length=200)
    length = models.IntegerField(_("Length"))
    width = models.IntegerField(_("Width"))
    height = models.IntegerField(_("Height"))
    weight = models.IntegerField(_("Weight (lbs)"))
    quantity = models.IntegerField(_("Quantity"))
    is_dg = models.BooleanField(_("Dangerous Goods"), default=False)
    note = models.CharField(_("Notes"), max_length=200, null=True, blank=True)
    is_arrival = models.BooleanField(_("Arriving"), default=False)
    is_departure = models.BooleanField(_("Departing"), default=False)

    class Meta:
        db_table = 'handling_requests_payloads_cargo'
        app_label = 'handling'
        ordering = ['id']
