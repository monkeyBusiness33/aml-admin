from django.db import models
from django.utils.translation import gettext_lazy as _


class Currency(models.Model):
    code = models.CharField(_("Code"), max_length=3, db_index=True)
    name = models.CharField(_("Name"), max_length=50)
    name_plural = models.CharField(_("Name (Plural)"), max_length=50)
    symbol = models.CharField(_("Symbol"), max_length=50)
    division_name = models.CharField(_("Division Name"), max_length=50,
                                     null=True, blank=True,
                                     )
    division_factor = models.BigIntegerField(_("Division Factor"), null=True, blank=True)
    
    class Meta:
        db_table = 'currencies'

    def __str__(self):
        return self.name
