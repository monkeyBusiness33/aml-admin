from django.db import models
from django.utils.translation import gettext_lazy as _
from core.forms import phone_regex_validator
from django.db.models import Q, F, Case, When, Value, CharField
from django.db.models.functions import Concat

from core.utils.datatables_functions import get_datatable_badge


class IpaDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        on_delete=models.CASCADE,
                                        related_name='ipa_details')
    iata_code = models.CharField(_("IATA Code"), max_length=10, null=True)

    class Meta:
        db_table = 'organisations_ipa_details'

    def __str__(self):
        return f'{self.organisation}'


class IpaLocationManager(models.Manager):
    def with_airport_details(self):
        return self.annotate(icao_iata=Case(
            When(Q(location__airport_details__iata_code__isnull=True)
                 | Q(location__airport_details__iata_code=''), then=F(
                'location__airport_details__icao_code')),
            When(Q(location__airport_details__icao_code__isnull=True)
                 | Q(location__airport_details__icao_code=''), then=F(
                'location__airport_details__iata_code')),
            default=Concat(
                'location__airport_details__icao_code',
                Value(' / '),
                'location__airport_details__iata_code',
                output_field=CharField()
            )))


class IpaLocation(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     related_name='ipa_locations_rev',
                                     on_delete=models.CASCADE)
    location = models.ForeignKey("organisation.Organisation",
                                 limit_choices_to={'details__type_id': 8,
                                                   'airport_details__isnull': False},
                                 on_delete=models.CASCADE,
                                 related_name='ipa_locations_here')

    fuel = models.ManyToManyField("core.FuelType",
                                  through='organisation.IpaLocationFuel',
                                  blank=True, related_name='ipa_locations')
    location_email = models.EmailField(_("Email"), max_length=254, null=True, blank=True)
    location_phone = models.CharField(_("Phone"), max_length=128, null=True, blank=True,
                                      validators=[phone_regex_validator])

    objects = IpaLocationManager()

    class Meta:
        db_table = 'organisations_ipa_locations'

    def __str__(self):
        return f'{self.pk}'

    @property
    def fuel_types_names(self):
        from core.models import FuelType
        location_fuel_types_list = FuelType.objects.filter(
            Q(ipa_location_equipment__ipa_location=self) |
            Q(ipa_locations_fuel__ipa_location=self)
        ).values_list('name', flat=True).distinct()
        return list(location_fuel_types_list)

    @property
    def location_fuel_types_badges(self):
        return ''.join([get_datatable_badge(
            badge_text=fuel_type,
            badge_class='bg-gray-600 p-1 me-1',
        ) for fuel_type in self.fuel_types_names])


class IpaLocationEquipment(models.Model):
    ipa_location = models.ForeignKey("organisation.IpaLocation",
                                     on_delete=models.CASCADE,
                                     related_name='equipment')
    name = models.CharField(_("Name"), max_length=50)
    registration = models.CharField(_("Registration"), max_length=50, null=True, blank=True)
    type = models.ForeignKey("core.FuelEquipmentType", verbose_name=_("Type"),
                             on_delete=models.CASCADE,
                             related_name='ipa_location_equipment')
    fuel_type = models.ForeignKey("core.FuelType", verbose_name=_("Fuel Type"),
                                  on_delete=models.CASCADE,
                                  related_name='ipa_location_equipment')
    fuel_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("UOM"),
                                 on_delete=models.CASCADE,
                                 related_name='ipa_location_equipment')
    temperature_unit = models.ForeignKey("core.TemperatureUnit",
                                         verbose_name=_("Temperature Unit"),
                                         on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_ipa_locations_equipment'

    def __str__(self):
        return f'{self.name}'


class IpaLocationFuel(models.Model):
    ipa_location = models.ForeignKey("organisation.IpaLocation",
                                     on_delete=models.CASCADE,
                                     related_name='location_fuel')
    fuel_type = models.ForeignKey("core.FuelType", verbose_name=_("Fuel Type"),
                                  on_delete=models.CASCADE,
                                  related_name='ipa_locations_fuel')

    class Meta:
        db_table = 'organisations_ipa_locations_fuel'

    def __str__(self):
        return f'{self.fuel_type}'
