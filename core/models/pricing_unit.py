from django.db import models
from django.utils.translation import gettext_lazy as _


class PricingUnit(models.Model):
    unit_code = models.CharField(_("Unit Code"), max_length=15)
    description = models.CharField(_("Description"), max_length=100, null=True, blank=True)
    uom = models.ForeignKey("core.UnitOfMeasurement",
                            verbose_name=_("Unit Of Measurement"),
                            on_delete=models.CASCADE)
    currency = models.ForeignKey("core.Currency", 
                                 verbose_name=_("Currency"), 
                                 on_delete=models.CASCADE)
    currency_division_used = models.BooleanField(_("Currency Division Used"), 
                                                 default=False)
    description_short = models.CharField(_("Short Description"), max_length=20, null=True, blank=True)
    
    class Meta:
        db_table = 'pricing_units'
        app_label = 'core'
        ordering = ['description']

    def __str__(self):
        return self.unit_code
