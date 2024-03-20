from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Case, When


class UnitOfMeasurementManager(models.Manager):
    def fluid_with_custom_ordering(self):
        custom_order = [2, 1, 5, 11, 10, 8, 4, 12, 13, 9, 6, 3]
        ordering = [When(id=id_val, then=pos) for pos, id_val in enumerate(custom_order)]
        return self.filter(id__in=custom_order).order_by(Case(*ordering))


class UnitOfMeasurement(models.Model):
    description = models.CharField(_("Description"), max_length=50)
    description_plural = models.CharField(_("Description Plural"), max_length=50)
    code = models.CharField(_("Short Code"), max_length=5)
    is_fluid_uom = models.BooleanField(_("Is Fluid UOM?"), default=False)
    is_mass_uom = models.BooleanField(_("Is Mass UOM?"), default=False)
    is_volume_uom = models.BooleanField(_("Is Volume UOM?"), default=False)

    objects = UnitOfMeasurementManager()

    class Meta:
        db_table = 'uom'
        app_label = 'core'
        ordering = ['description']

    def __str__(self):
        return self.description_plural

    def to_usg(self, fuel_quantity, source=None):
        if not source:
            source = UnitOfMeasurementSource.objects.get(code='STD')

        uom_conversion_factor = self.conversion_factors.filter(source=source).first().usg_conversion_factor
        return uom_conversion_factor * fuel_quantity


class UnitOfMeasurementSource(models.Model):
    code = models.CharField(_("Code"), max_length=6)

    class Meta:
        db_table = 'uom_sources'
        app_label = 'core'

    def __str__(self):
        return self.code


class UnitOfMeasurementConversionFactor(models.Model):
    uom = models.ForeignKey(UnitOfMeasurement, verbose_name=_("Unit of Measurement"),
                            on_delete=models.CASCADE,
                            related_name='conversion_factors',
                            )
    conversion_factor_to_litre = models.DecimalField(_("Conversion Factor to Litre"), max_digits=12, decimal_places=8)
    source = models.ForeignKey(UnitOfMeasurementSource, verbose_name=_("Source"), on_delete=models.CASCADE)
    specific_fuel = models.ForeignKey("core.FuelType", verbose_name=_("Specific Fuel"),
                                      on_delete=models.CASCADE, null=True,
                                      related_name='uom_conversions_ratio_to_l_for_this_fuel')
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   db_column='updated_by', on_delete=models.RESTRICT,
                                   default=7)

    class Meta:
        db_table = 'uom_conversion_factors'
        app_label = 'core'

    def __str__(self):
        return f'{self.uom}'


class UnitOfMeasurementConversionMethod(models.Model):
    uom_converting_from = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Unit of Measurement"),
                                            on_delete=models.CASCADE, db_column='uom_converting_from',
                                            related_name='conversion_from_methods',
                                            )
    uom_converting_to = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Unit of Measurement"),
                                          on_delete=models.CASCADE, db_column='uom_converting_to',
                                          related_name='conversion_to_methods',
                                          )
    conversion_ratio_div = models.DecimalField(_("Conversion Ratio"), max_digits=12, decimal_places=4)
    specific_fuel = models.ForeignKey("core.FuelType", verbose_name=_("Specific Fuel"),
                                      on_delete=models.CASCADE, null=True,
                                      related_name='uom_conversions_specific_for_this_fuel')
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   db_column='updated_by', on_delete=models.RESTRICT)

    class Meta:
        db_table = 'uom_conversion_methods'

    def __str__(self):
        return f"{self.uom_converting_from} -> {self.uom_converting_to}"


class TemperatureUnit(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'uom_temperature'
        app_label = 'core'

    def __str__(self):
        return self.name
