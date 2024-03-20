from django.db import models
from django.utils.translation import gettext_lazy as _


class DlaContractLocationManager(models.Manager):
    def get_handling_request_contract(self, handling_request):
        """
        Returns active contracts for the S&F Request
        :param handling_request: HandlingRequest object
        :return:
        """
        return self.filter(
            is_active=True,
            location=handling_request.airport,
            start_date__lte=handling_request.arrival_movement.date,
            end_date__gte=handling_request.departure_movement.date,
        )


class DLAContractLocation(models.Model):
    supplier = models.ForeignKey("organisation.Organisation",
                                 related_name='dla_contracted_locations_rev',
                                 on_delete=models.CASCADE, null=True
                                 )
    location = models.ForeignKey("organisation.Organisation",
                                 on_delete=models.CASCADE,
                                 related_name='dla_contracted_locations_here',
                                 )
    contract_reference = models.CharField(_("Contract Reference"), max_length=50)
    start_date = models.DateField(_("Start Date"), auto_now=False, auto_now_add=False)
    end_date = models.DateField(_("End Date"), auto_now=False, auto_now_add=False)
    early_termination_date = models.DateField(_("Early Termination Date"),
                                              auto_now=False, auto_now_add=False,
                                              null=True,
                                              )
    is_active = models.BooleanField(_("Is Active"), default=True)
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            related_name="dla_contracted_locations_ipa_rev",
                            on_delete=models.CASCADE,
                            null=True)
    cis_supplier_name = models.ForeignKey("dla_scraper.DLASupplierName", verbose_name=_("CIS Supplier Name"),
                                          related_name="dla_contracts_using_supplier_name",
                                          on_delete=models.RESTRICT,
                                          null=True)
    cis_ipa_name = models.ForeignKey("dla_scraper.DLASupplierName", verbose_name=_("CIS IPA Name"),
                                     related_name="dla_contracts_using_ipa_name",
                                     on_delete=models.RESTRICT,
                                     null=True)
    expiring_email_sent = models.BooleanField(_("Expiring Email Sent"), default=False)
    enforce_fuel_order = models.BooleanField(_("Enforce Fuel Order?"), default=False)

    objects = DlaContractLocationManager()

    class Meta:
        db_table = 'organisations_dla_contracts'
        permissions = [
            ('view_dla_scraper', 'Can view DLA scraper logs'),
            ('run_dla_scraper', 'Can run DLA scraper'),
        ]

    def __str__(self):
        return f'{self.pk}'
