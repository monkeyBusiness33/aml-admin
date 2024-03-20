from django.db import models
from django.utils.translation import gettext_lazy as _


class OrganisationOpsDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation", verbose_name=_("Organisation"),
                                        related_name='ops_details',
                                        on_delete=models.CASCADE)
    receives_parking_chase_email = models.BooleanField(_("Receives Automated Parking Chase Emails?"), default=True)
    spf_use_aml_logo = models.BooleanField(_("Use AML Logo in SPF?"), default=True)

    class Meta:
        db_table = 'organisations_ops_details'

    def __str__(self):
        return f'{self.pk}'
