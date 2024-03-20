from django.db import models
from solo.models import SingletonModel
from django.utils.translation import gettext_lazy as _


class GlobalConfiguration(SingletonModel):
    dod_cs_ts = models.TextField(_("DoD Terms & Conditions"), null=True, blank=True)

    def __str__(self):
        return "Global Configuration"

    class Meta:
        verbose_name = "Global Configuration"
        db_table = "settings"
