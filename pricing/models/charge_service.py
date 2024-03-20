from django.db import models
from django.utils.translation import gettext_lazy as _


class ChargeServiceCategory(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    
    class Meta:
        db_table = 'charge_services_categories'

    def __str__(self):
        return self.name


class ChargeService(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    category = models.ForeignKey("pricing.ChargeServiceCategory", 
                                 verbose_name=_("Category"), 
                                 on_delete=models.CASCADE)

    class Meta:
        db_table = 'charge_services'

    def __str__(self):
        return self.name
