from django.db import models
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    name = models.CharField(_("Name"), max_length=150)
    code = models.CharField(_("Code"), max_length=2, unique=True)
    continent = models.CharField(_("Continent"), max_length=2)
    currency = models.ForeignKey("core.Currency", verbose_name=_("Currency"),
                                 on_delete=models.CASCADE)
    in_eu = models.BooleanField(_("In EU?"), default=False)
    in_schengen = models.BooleanField(_("In Schengen?"), default=False)
    in_eea = models.BooleanField(_("In EAA?"), default=False)
    in_cemac = models.BooleanField(_("In CEMAC?"), default=False)
    in_ecowas = models.BooleanField(_("In ECOWAS?"), default=False)
    is_in_nato = models.BooleanField(_("In NATO?"), default=False)

    class Meta:
        ordering = ['name']
        db_table = 'countries'

    def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(_("Name"), max_length=150, null=True, blank=True)
    code = models.CharField(_("Code"), max_length=10)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.CASCADE, related_name='regions')

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return self.code
