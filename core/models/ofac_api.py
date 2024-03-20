from django.db import models
from django.utils.translation import gettext_lazy as _


class OfacApiException(models.Model):
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Excepted Organisation"),
                                     related_name="ofac_excepted", on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_ofac_api_exceptions'

    def __str__(self):
        return f'{self.organisation.pk}'
