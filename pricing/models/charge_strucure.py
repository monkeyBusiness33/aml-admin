from django.db import models
from django.utils.translation import gettext_lazy as _


class ChargeStructureCode(models.Model):
    code = models.CharField(_("Code"), max_length=12)
    name = models.CharField(_("Name"), max_length=60)

    class Meta:
        db_table = 'charge_structure_codes'

    def __str__(self):
        return self.code


class ChargeStructureQualifier(models.Model):
    code = models.CharField(_("Code"), max_length=10)
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'charge_structure_qualifiers'

    def __str__(self):
        return self.code


class ChargeBand(models.Model):
    type = models.CharField(_("Code"), max_length=6)
    name = models.CharField(_("Name"), max_length=80)
    reference = models.CharField(_("Reference"), max_length=60)

    class Meta:
        db_table = 'charge_bands'

    def __str__(self):
        return self.name


class ChargeStructureProperties(models.Model):
    structure_code = models.ForeignKey("pricing.ChargeStructureCode", 
                                       verbose_name=_("Charge Structure Code"), 
                                       on_delete=models.CASCADE)
    description = models.CharField(_("Description"), max_length=250)
    structure_qualifier = models.ForeignKey("pricing.ChargeStructureQualifier", 
                                            verbose_name=_("Charge Structure Qualifier"), 
                                            null=True, blank=True,
                                            on_delete=models.CASCADE)
    band_1 = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 1"), 
                               null=True, blank=True,
                               related_name='charge_structure_properties_band_1',
                               on_delete=models.CASCADE)
    band_2 = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 2"),
                               null=True, blank=True,
                               related_name='charge_structure_properties_band_2',
                               on_delete=models.CASCADE)
    icao_noise_chapter_included = models.BooleanField(_("ICAO Noice Chapter Included"), default=False)
    class_specific = models.BooleanField(_("Class Specific"), default=False)
    type_specific = models.BooleanField(_("Type Specific"), default=False)
    custom_calculation_code = models.BooleanField(_("Custom Calculation Code"), default=False)
    is_active = models.BooleanField(_("Is Active?"), default=True)
    is_draft = models.BooleanField(_("Is Draft?"), default=False)

    class Meta:
        db_table = 'charge_structures_properties'

    def __str__(self):
        return self.description
