from django.db import models
from django.utils.translation import gettext_lazy as _


class AmlApplication(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    code = models.SlugField(_("Code Name"), max_length=20, db_index=True, unique=True)

    class Meta:
        ordering = ['name']
        db_table = 'aml_applications'

    def __str__(self):
        return self.name
