from django.db import models
from django.utils.translation import gettext_lazy as _


class ADS_Country(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Name"), max_length=150)
    code = models.CharField(_("Code"), max_length=2)
    continent = models.CharField(_("Continent"), max_length=2)
    currency_code = models.CharField(_("Code"), max_length=50)
    in_eu = models.BooleanField(_("In EU?"), default=False)
    in_schengen = models.BooleanField(_("In Schengen?"), default=False)
    in_eea = models.BooleanField(_("In EAA?"), default=False)
    in_cemac = models.BooleanField(_("In CEMAC?"), default=False)
    in_ecowas = models.BooleanField(_("In ECOWAS?"), default=False)

    class Meta:
        db_table = 'countries'
        managed = False

    def __str__(self):
        return self.name


class ADS_Region(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Name"), max_length=150, null=True, blank=True)
    code = models.CharField(_("Code"), max_length=10)
    country = models.ForeignKey(ADS_Country, verbose_name=_("Country"), 
                                   on_delete=models.CASCADE,
                                   )
    
    class Meta:
        db_table = 'regions'
        managed = False

    def __str__(self):
        return self.code

        
class ADS_Currency(models.Model):
    id = models.AutoField(primary_key=True)
    currency_code = models.CharField(_("Code"), max_length=3)
    currency_name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'currencies'
        managed = False

    def __str__(self):
        return self.name


class ADS_AirportMaxWeightUnit(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'airports_max_weight_units'
        managed = False

    def __str__(self):
        return self.name
    
class ADS_Airport(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    icao_code = models.CharField(_("ICAO Code"), max_length=4, unique=True)
    name = models.CharField(_("Name"), max_length=100)
    iata_code = models.CharField(_("IATA Code"), max_length=3, null=True, blank=True)
    region = models.ForeignKey(ADS_Region, verbose_name=_("Region"),
                               on_delete=models.CASCADE
                               )
    latitude = models.DecimalField(_('Latitude'), max_digits=10, decimal_places=8)
    longitude = models.DecimalField(_('Longitude'), max_digits=11, decimal_places=8)
    maximum_weight = models.IntegerField(_("Maximum Weight"))
    maximum_weight_unit = models.ForeignKey(ADS_AirportMaxWeightUnit, 
                                               verbose_name=_("Maximum Weight Unit"), 
                                               on_delete=models.CASCADE)
    currency_override = models.ForeignKey(ADS_Currency, verbose_name=_("Currency Override"),
                                          null=True, blank=True, 
                                          on_delete=models.CASCADE,
                                          db_column='currency_override',
                                          )
    active = models.BooleanField(_("Is Active?"), default=True)
    has_structures = models.BooleanField(_("Has Pricing"), default=False)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True, auto_now_add=False)
    updated_by = models.IntegerField(_("Updated by"))

    class Meta:
        db_table = 'airports'
        managed = False

    def __str__(self):
        return self.icao_code


class ADS_AircraftType(models.Model):
    id = models.BigAutoField(_("ID"), primary_key=True)
    designator = models.CharField(_("ICAO Type"), max_length=4, 
                                  db_column='type_designator')
    manufacturer = models.CharField(_("Manufacturer"), max_length=40, 
                                    db_column='type_manufacturer')
    model = models.CharField(_("Model"), max_length=50, db_column='type_model')
    category = models.CharField(_("Category"), max_length=40)

    class Meta:
        db_table = 'aircraft_types'
        managed = False

    def __str__(self):
        return f'{self.manufacturer} {self.model} ({self.designator})'


class ADS_Aircraft(models.Model):
    id = models.BigAutoField(_("ID"), primary_key=True)
    asn = models.CharField(_("ASN"), max_length=35, null=True)
    ads_asn = models.CharField(_("ADS ASN"), max_length=50, null=True)
    type = models.ForeignKey(ADS_AircraftType, verbose_name=_("Aircraft Type"),
                             null=True, on_delete=models.SET_NULL,
                             )
    pax_seats = models.IntegerField(_("Pax Seats"), null=True)
    yom = models.IntegerField(_("YOM"), null=True)
    source = models.CharField(_("Source"), max_length=6, default='AML')
    is_decommissioned = models.BooleanField(_("Decommissioned"), default=False)
    created_at = models.DateTimeField(
        _("Created at"), auto_now=False, auto_now_add=True)
    details_id = models.BigIntegerField()

    class Meta:
        db_table = 'aircraft'
        managed = False

    def __str__(self):
        return f'{self.ads_asn}'


class ADS_AircraftHistory(models.Model):
    aircraft = models.ForeignKey(ADS_Aircraft, verbose_name=_("Aircraft"), on_delete=models.CASCADE,
                                 related_name='aircraft_history',
                                 )
    registration = models.CharField(_("Registration"), max_length=50)
    operator_id = models.BigIntegerField(null=True)
    homebase = models.ForeignKey(ADS_Airport, verbose_name=_("Homebase"), on_delete=models.CASCADE)
    change_effective_date = models.DateField(_("Change Date"), auto_now=False, auto_now_add=False)
    source = models.CharField(_("Source"), max_length=6)
    created_at = models.DateTimeField(_("Created at"), auto_now=False, auto_now_add=False)
    created_by = models.IntegerField(_("Created by"))
    
    class Meta:
        db_table = 'aircraft_history'
        managed = False

    def __str__(self):
        return f'{self.registration}'