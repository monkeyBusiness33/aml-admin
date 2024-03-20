from django.db import models
from django.utils.translation import gettext_lazy as _

class PricingCalculationRecord(models.Model):
    scenario = models.JSONField(_("Pricing Scenario"), blank=False, null=False)
    results = models.JSONField(_("Pricing Results"), blank=False, null=False)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"),
                                   null=True, on_delete=models.SET_NULL,
                                   related_name='created_pricing_calculation_record')

    class Meta:
        db_table='fuel_pricing_calculations_history'