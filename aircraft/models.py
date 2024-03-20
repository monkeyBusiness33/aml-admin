from django.db import models
from django.utils.translation import gettext_lazy as _
from .tasks import delete_conflicting_test_aircraft


class AircraftManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(test_aircraft=False)

    def include_test_aircraft(self):
        return super().get_queryset()

    def get_test_aircraft(self):
        return super().get_queryset().filter(test_aircraft=True)


class AircraftHistoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(aircraft__test_aircraft=False)

    def include_test_aircraft(self):
        return super().get_queryset()


class AircraftDesignator(models.Model):
    icao = models.CharField(_("ICAO"), max_length=10)
    iata = models.CharField(_("IATA"), max_length=10, null=True, blank=True)
    wtc = models.CharField(_("WTC"), max_length=1, null=True, blank=True)

    class Meta:
        db_table = 'aircraft_designators'

    def __str__(self):
        return f'{self.icao}'


class AircraftType(models.Model):
    designator = models.CharField(_("ICAO Type"), max_length=4)
    manufacturer = models.CharField(_("Manufacturer"), max_length=40)
    model = models.CharField(_("Name"), max_length=50)
    category = models.CharField(_("Category"), max_length=3)
    mtow_indicative_kg = models.BigIntegerField(_("MTOW Indicative KG"), null=True, blank=True)
    mtow_indicative_lbs = models.BigIntegerField(_("MTOW Indicative LBS"), null=True, blank=True)
    maximum_fuel_indicative_litres = models.BigIntegerField(_("MTOW Indicative LBS"), null=True, blank=True)
    type_designator = models.ForeignKey("aircraft.AircraftDesignator", verbose_name=_("Designator"),
                                        related_name='aircraft_types',
                                        null=True,  # TODO: Temporary, Remove this
                                        on_delete=models.CASCADE)

    class Meta:
        db_table = 'aircraft_types'
        ordering = ['manufacturer']

    def __str__(self):
        return f'{self.manufacturer} {self.model} ({self.designator})'


class Aircraft(models.Model):
    asn = models.CharField(_("ASN"), max_length=35, null=True, blank=True)
    ads_asn = models.CharField(_("ADS ASN"), max_length=50, null=True)
    type = models.ForeignKey(AircraftType, verbose_name=_("Aircraft Type"),
                             related_name='aircraft_list',
                             null=True, on_delete=models.SET_NULL,
                             )
    pax_seats = models.IntegerField(_("Pax Seats"), null=True, blank=True)
    yom = models.IntegerField(_("YOM"), null=True)
    source = models.CharField(_("Source"), max_length=6, default='AML')
    is_decommissioned = models.BooleanField(_("Decommissioned"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now=False, auto_now_add=True)
    details = models.OneToOneField("aircraft.AircraftHistory", null=True, on_delete=models.SET_NULL,
                                   related_name='details_rev')
    test_aircraft = models.BooleanField(_("Is Test Aircraft?"), default=False)

    # A manager excluding test aircraft (for most purposes)
    objects = AircraftManager()

    class Meta:
        db_table = 'aircraft'

    def __str__(self):
        return f'{self.pk}'

    def save(self, *args, **kwargs):
        if not self.ads_asn and self.type:
            self.ads_asn = f'{self.type.designator}-{self.type.id}-{self.asn}'
        super().save(*args, **kwargs)


class AircraftHistory(models.Model):
    aircraft = models.ForeignKey(Aircraft, verbose_name=_("Aircraft"), on_delete=models.CASCADE,
                                 related_name='aircraft_history',
                                 )
    registration = models.CharField(_("Registration"), max_length=50)
    operator = models.ForeignKey("organisation.Organisation", verbose_name=_("Operator"),
                                 null=True, blank=True,
                                 on_delete=models.CASCADE,
                                 related_name='aircraft_list',
                                 )
    homebase = models.ForeignKey("organisation.Organisation", verbose_name=_("Homebase"),
                                 limit_choices_to={'details__type_id': 8,
                                                   'airport_details__isnull': False},
                                 null=True, blank=True,
                                 on_delete=models.CASCADE)
    change_effective_date = models.DateField(_("Change Date"), auto_now=False, auto_now_add=True)
    source = models.CharField(_("Source"), max_length=6, default='AML')
    created_at = models.DateTimeField(_("Created at"), auto_now=False, auto_now_add=True)

    registered_country = models.ForeignKey("core.Country", verbose_name=_("Country of Registration"),
                                           null=True, on_delete=models.SET_NULL)

    # A manager excluding test aircraft (for most purposes)
    objects = AircraftHistoryManager()

    class Meta:
        db_table = 'aircraft_history'

    def __str__(self):
        return f'{self.registration}'

    def save(self, *args, **kwargs):
        self.pk = None
        super().save(*args, **kwargs)
        if self.pk:
            Aircraft.objects.filter(
                pk=self.aircraft.pk).update(details=self)

        # Silently delete test aircraft with conflicting ads_asn / registration
        delete_conflicting_test_aircraft.delay(self.aircraft.pk, self.aircraft.ads_asn, self.registration)


class AircraftTypeApprovedFuel(models.Model):
    aircraft_type = models.ForeignKey("AircraftType", verbose_name=_("Aircraft Type"),
                                      on_delete=models.CASCADE,
                                      related_name='fuel_types_approved')
    fuel_type = models.ForeignKey("core.FuelType", verbose_name=_("Fuel Type"),
                                  on_delete=models.CASCADE,
                                  related_name='aircraft_types_approved')
    specific_operator = models.ForeignKey("organisation.Organisation", verbose_name=_("Specific Operator"),
                                          null=True, on_delete=models.CASCADE,
                                          related_name='aircraft_types_approved_fuel')

    class Meta:
        db_table = 'aircraft_types_approved_fuel'
        ordering = ['aircraft_type__manufacturer']

    def __str__(self):
        return f'{self.aircraft_type} - {self.fuel_type}' + \
               (f' ({self.specific_operator.details.registered_name})' if self.specific_operator else '')


class AircraftWeightUnit(models.Model):
    name = models.CharField(_("Unit name"), max_length=50)

    class Meta:
        db_table = 'aircraft_weight_units'

    def __str__(self) -> str:
        return f'{self.name}'
