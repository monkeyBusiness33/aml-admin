from django.db import models
from django.utils.translation import gettext_lazy as _


class NasdlType(models.Model):
    description = models.CharField(_("Description"), max_length=50)

    class Meta:
        db_table = 'organisations_nasdl_types'

    def __str__(self):
        return f'{self.description}'


class NasdlDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        on_delete=models.CASCADE,
                                        related_name='nasdl_details')
    type = models.ForeignKey("organisation.NasdlType",
                             verbose_name=_("Type"),
                             on_delete=models.RESTRICT)
    latitude = models.DecimalField(_('Latitude'), max_digits=10, decimal_places=8,
                                   null=True, blank=True)
    longitude = models.DecimalField(_('Longitude'), max_digits=11, decimal_places=8,
                                    null=True, blank=True)
    what3words_code = models.CharField(_("What3Words Code"), max_length=255,
                                       null=True, blank=True)
    use_address = models.BooleanField(_("Use Address for Location?"), default=False)
    comment_guidance = models.CharField(_("Location Comments / Guidance"), max_length=500,
                                        null=True, blank=True)

    class Meta:
        db_table = 'organisations_nasdl_details'

    def __str__(self):
        return f'{self.organisation.details.registered_name}'

    @property
    def physical_address(self):
        return self.organisation.addresses.filter(is_physical_address=True).first()
