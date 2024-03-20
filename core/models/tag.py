from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    description = models.CharField(_("Description"), max_length=100, null=True, blank=True)
    is_system = models.BooleanField(_("Is System Tag?"), default=False)

    class Meta:
        db_table = 'tags'
    
    def __str__(self):
        return f'{self.name}'