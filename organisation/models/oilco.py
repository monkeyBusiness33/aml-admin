from django.db import models
from django.utils.translation import gettext_lazy as _


class OilcoDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        on_delete=models.CASCADE,
                                        related_name='oilco_details')
    iata_code = models.CharField(_("IATA Code"), max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'organisations_oilco_details'

    def __str__(self):
        return f'{self.organisation}'


class OilcoFuelType(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     on_delete=models.CASCADE,
                                     related_name='oilco_fuel')
    fuel_type = models.ForeignKey("core.FuelType", verbose_name=_("Fuel Type"),
                                  on_delete=models.CASCADE,
                                  related_name='oilco_fuel_types')

    class Meta:
        db_table = 'organisations_oilco_fuel_types'

    def __str__(self):
        return f'{self.fuel_type}'
