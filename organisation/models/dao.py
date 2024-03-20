from django.db import models
from django.utils.translation import gettext_lazy as _


class DaoDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation", on_delete=models.CASCADE,
                                   related_name='dao_details')
    contact_email_1 = models.EmailField(_("Email 1"), max_length=254, null=True, blank=True)
    contact_email_2 = models.EmailField(_("Email 2"), max_length=254, null=True, blank=True)
    contact_phone_1 = models.CharField(_("Phone 1"), max_length=500, null=True, blank=True)
    contact_phone_2 = models.CharField(_("Phone 2"), max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'organisations_dao_details'

    def __str__(self):
        return f'{self.organisation.id}'


class DaoCountry(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     on_delete=models.CASCADE)
    responsible_country = models.ForeignKey("core.Country", verbose_name=_("Country"),
                                               on_delete=models.CASCADE, 
                                               related_name='country_dao')

    class Meta:
        db_table = 'organisations_dao_countries'

    def __str__(self):
        return f'{self.organisation}'
