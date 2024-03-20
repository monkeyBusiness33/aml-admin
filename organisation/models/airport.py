from datetime import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


class AirportWeightUnit(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    
    class Meta:
        ordering = ['name']
        db_table = 'organisations_airports_weight_units'

    def __str__(self):
        return self.name


class AirportDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation", on_delete=models.CASCADE,
                                        related_name='airport_details')
    authority = models.ForeignKey("organisation.Organisation", verbose_name=_("Authority"),
                                  null=True, blank=True,
                                  on_delete=models.CASCADE)
    icao_code = models.CharField(_("ICAO Code"), max_length=4, null=True, blank=True, unique=True)
    iata_code = models.CharField(_("IATA Code"), max_length=3, null=True, blank=True)
    region = models.ForeignKey("core.Region", verbose_name=_("Region"), on_delete=models.RESTRICT)
    latitude = models.DecimalField(_('Latitude'), max_digits=10, decimal_places=8)
    longitude = models.DecimalField(_('Longitude'), max_digits=11, decimal_places=8)
    maximum_weight = models.IntegerField(_("Maximum Weight"))
    maximum_weight_unit = models.ForeignKey(AirportWeightUnit, verbose_name=_("Maximum Weight Unit"),
                                            on_delete=models.CASCADE)
    website_url = models.URLField(_("Website URL"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=False, auto_now_add=False, default=datetime.now)
    updated_by_ads_person_id = models.BigIntegerField(_("Updated By ADS Person"), null=True)

    class Meta:
        db_table = 'organisations_airports_details'

    def __str__(self):
        return self.icao_code
    
    @property
    def icao_iata(self):
        """
        Property to return formatted ICAO/IATA string
        :return: string
        """
        if self.iata_code:
            return f'{self.icao_code} / {self.iata_code}'
        else:
            return f'{self.icao_code}'
    
    @property
    def fullname(self):
        fullname = f'{self.organisation.details.registered_name} ({self.icao_code}'
        if self.iata_code:
            fullname += f'/{self.iata_code}'
        fullname += ')'
        return fullname
