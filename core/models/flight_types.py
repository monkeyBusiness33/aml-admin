from django.db import models
from django.utils.translation import gettext_lazy as _


class FlightType(models.Model):
    code = models.CharField(_("Code"), max_length=1, primary_key=True)
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        ordering = ['name']
        db_table = 'flight_types'

    def __str__(self):
        return self.name


class GeographichFlightType(models.Model):
    code = models.CharField(_("Code"), max_length=10, primary_key=True)
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        ordering = ['name']
        db_table = 'flight_types_geographic'

    def __str__(self):
        return self.name
