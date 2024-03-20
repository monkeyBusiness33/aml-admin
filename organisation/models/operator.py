from django.db import models
from django.utils.translation import gettext_lazy as _
from core.forms import phone_regex_validator


class OperatorType(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    operates_private_flights = models.BooleanField(_("Private Flights"), default=False)
    operates_public_transport_flights = models.BooleanField(_("Public Transport Flights"), default=False)
    operates_government_flights = models.BooleanField(_("Government Flights"), default=False)
    operates_military_flights = models.BooleanField(_("Military Flights"), default=False)
    operates_training_flights = models.BooleanField(_("Training Flights"), default=False)
    operates_air_work_flights = models.BooleanField(_("Air Work Flights"), default=False)
    operates_air_ambulance_flights = models.BooleanField(_("Air Ambulance Flights"), default=False)
    operates_special_mission_flights = models.BooleanField(_("Special Mission Flights"), default=False)
    operates_scheduled_passenger_flights = models.BooleanField(_("Scheduled Passenger Flights"), default=False)
    operates_scheduled_cargo_flights = models.BooleanField(_("Scheduled Cargo Flights"), default=False)
    operates_non_scheduled_passenger_flights = models.BooleanField(_("Non-Scheduled Passenger Flights"), default=False)
    operates_non_scheduled_cargo_flights = models.BooleanField(_("Non-Scheduled Cargo Flights"), default=False)

    class Meta:
        ordering = ['name']
        db_table = 'organisations_operator_types'

    def __str__(self):
        return f'{self.name}'


class OperatorDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        on_delete=models.CASCADE,
                                        related_name='operator_details')
    type = models.ForeignKey("organisation.OperatorType",
                             verbose_name=_("Operator Type"), on_delete=models.CASCADE)
    ads_operator_id = models.BigIntegerField(_("ADS Operator ID"), null=True, blank=True)
    contact_email = models.EmailField(_("Contact Email Address"), max_length=254, null=True)
    contact_phone = models.CharField(_("Contact Phone Number"), max_length=128, null=True,
                                     validators=[phone_regex_validator])
    commercial_email = models.EmailField(_("Commercial Email Address"), max_length=254, null=True, blank=True)
    commercial_phone = models.CharField(_("Commercial Phone Number"), max_length=128, null=True, blank=True,
                                        validators=[phone_regex_validator])
    ops_email = models.EmailField(_("Operations Email Number"), max_length=254, null=True, blank=True)
    ops_phone = models.CharField(_("Operations Phone Number"), max_length=128, null=True, blank=True,
                                 validators=[phone_regex_validator])

    crew_weight = models.IntegerField(_("Crew Weight"), null=True, blank=True)
    pax_weight_male = models.IntegerField(_("Pax Weight Male"), null=True, blank=True)
    pax_weight_female = models.IntegerField(_("Pax Weight Female"), null=True, blank=True)
    pax_crew_weight_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Pax & Crew Weight Unit"),
                                            null=True, blank=True,
                                            related_name='operators_pax_crew_weight',
                                            on_delete=models.SET_NULL)

    class Meta:
        db_table = 'organisations_operator_details'

    def __str__(self):
        return f'{self.pk}'


class OperatorPreferredGroundHandler(models.Model):
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Organisation"),
                                     limit_choices_to={'operator_details__isnull': False},
                                     related_name='operator_preferred_handlers',
                                     on_delete=models.CASCADE)
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 limit_choices_to={'details__type_id': 8,
                                                   'airport_details__isnull': False},
                                 related_name='location_preferred_handlers',
                                 on_delete=models.CASCADE)
    ground_handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Preferred Ground Handler"),
                                       limit_choices_to={'handler_details__isnull': False},
                                       related_name='preferred_handler_operators',
                                       on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_operators_preferred_handlers'

    def __str__(self):
        return f'{self.pk}'
