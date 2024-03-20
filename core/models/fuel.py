from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Case, When


class FuelTypeManager(models.Manager):
    def with_custom_ordering(self):
        custom_order = [1, 12, 6, 2, 13, 8, 11, 15, 14, 3, 4, 5, 9, 8, 10]
        ordering = [When(id=id_val, then=pos) for pos, id_val in enumerate(custom_order)]
        return self.filter(id__in=custom_order).order_by(Case(*ordering))


class FuelType(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    iata_code = models.CharField(_("IATA Code"), max_length=6,
                                 null=True, blank=True)
    nato_code = models.CharField(_("NATO Code"), max_length=10,
                                 null=True, blank=True)
    is_blend = models.BooleanField(_("Is Blend?"), default=False)
    sg_kg_ltr = models.DecimalField(_("SG (kg/ltr)"), max_digits=10, decimal_places=4, null=True)
    sg_lb_usg = models.DecimalField(_("SG (lb/usg)"), max_digits=10, decimal_places=4, null=True)
    category = models.ForeignKey("core.FuelCategory", verbose_name=_("Category"),
                                 on_delete=models.RESTRICT, related_name='fuel_types',
                                 null=True)

    objects = FuelTypeManager()

    class Meta:
        db_table = 'fuel_types'

    def __str__(self):
        return self.name

    @property
    def name_with_nato_code(self):
        if self.nato_code:
            return f'{self.name} ({self.nato_code})'
        else:
            return f'{self.name}'


class FuelCategory(models.Model):
    name = models.CharField(_("Name"), max_length=100)

    class Meta:
        db_table = 'fuel_categories'

    def __str__(self):
        return self.name


class FuelEquipmentType(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'fuel_equipment_types'
        ordering = ['name', ]

    def __str__(self):
        return self.name


class FuelAdditive(models.Model):
    code = models.CharField(_("Code"), max_length=10,
                            null=True, blank=True)
    name = models.CharField(_("Name"), max_length=50)
    is_fsii = models.BooleanField(_("Is FSII?"), default=False)
    is_lia = models.BooleanField(_("Is LIA?"), default=False)

    class Meta:
        db_table = 'fuel_additives'

    def __str__(self):
        return self.name


class FuelTypeBlend(models.Model):
    fuel = models.ForeignKey("core.FuelType", verbose_name=_("Fuel"),
                             on_delete=models.CASCADE,
                             related_name='blends')

    class Meta:
        db_table = 'fuel_types_blends'

    def __str__(self):
        return f'{self.pk}'


class FuelTypeBlendComponent(models.Model):
    fuel_blend = models.ForeignKey("FuelTypeBlend", verbose_name=_("Blend"),
                                   on_delete=models.CASCADE,
                                   related_name='components')
    fuel = models.ForeignKey("FuelType", verbose_name=_("Fuel"),
                             on_delete=models.CASCADE, null=True,
                             related_name='blends_with_fuel')
    fuel_additive = models.ForeignKey("FuelAdditive", verbose_name=_("Additive"),
                                      on_delete=models.CASCADE, null=True,
                                      related_name='blends_with_additive')
    component_blend_percentage = models.DecimalField(_("Component Blend Percentage"),
                                                     max_digits=6, decimal_places=4,
                                                     null=True)

    class Meta:
        db_table = 'fuel_types_blends_components'

    def __str__(self):
        return f'{self.pk}'


class HookupMethod(models.Model):
    code = models.CharField(_("Code"), max_length=2, primary_key=True)
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        ordering = ['name']
        db_table = 'fuel_hookup_methods'

    def __str__(self):
        return self.name
