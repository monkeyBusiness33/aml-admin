from django.db import models
from django.utils.translation import gettext_lazy as _


class ApronType(models.Model):
    name = models.CharField(_("Comment"), max_length=50)

    class Meta:
        db_table = 'apron_types'

    def __str__(self):
        return f'{self.name}'
