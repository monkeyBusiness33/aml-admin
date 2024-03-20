from django.db import models
from django.utils.translation import gettext_lazy as _
from organisation.models.dla_location import DLAContractLocation


class DLAContract(DLAContractLocation):
    class Meta:
        proxy = True
        managed = False

    def __str__(self):
        return f"{self.contract_reference} (" + \
               (f"{self.supplier.details.registered_name}; " if self.supplier else "") + \
               f"{self.start_date} - " \
               f"{self.early_termination_date if self.early_termination_date is not None else self.end_date})"


class DLASupplierName(models.Model):
    name = models.CharField(_("Supplier Name"), max_length = 100)
    supplier = models.ForeignKey("organisation.Organisation", verbose_name=_("Supplier"),
                                 related_name="dla_supplier_names", on_delete=models.CASCADE,
                                 null=True)

    class Meta:
        db_table = 'organisations_dla_suppliers_ids'
        managed = True
        ordering = ['id']
        permissions = [
            ('reconcile_dla_name', 'Can reconcile DLA names'),
        ]

    def __str__(self):
        return self.name


class DLALocationAlternativeIcaoCode(models.Model):
    icao_code = models.CharField(_("ICAO Code"), max_length = 4)
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 related_name="dla_location_alternative_icao_codes", on_delete=models.CASCADE,
                                 limit_choices_to={'details__type_id': 8}, null=True)

    class Meta:
        db_table = 'organisations_dla_alternative_icao_codes'
        managed = True
        ordering = ['location__airport_details__icao_code']
        permissions = [
            ('reconcile_dla_icao_code', 'Can reconcile alternative ICAO codes for DLA scraper'),
        ]

    def __str__(self):
        return f'{self.icao_code} ' + \
               (f'({self.location.airport_details.icao_code})' if self.location else '')


class DLAScraperRunStatus(models.Model):
    code = models.CharField(_("Status Code"), max_length = 10)
    
    class Meta:
        db_table = 'dla_scraper_run_status_types'
        managed = True
        ordering = ['id']

    def __str__(self):
        return self.code


class DLAScraperRun(models.Model):
    status = models.ForeignKey("dla_scraper.DLAScraperRunStatus", verbose_name=_("Run Status"),
                               related_name="runs_with_status", on_delete=models.RESTRICT,
                               null=False)
    run_at = models.DateTimeField(_("Run at"), auto_now=False, auto_now_add=True, null=False)
    log = models.JSONField(_("Run Log"), blank=True, null=True)
    is_scheduled = models.BooleanField(_("Was a scheduled run?"), default=False)
    
    class Meta:
        db_table = 'dla_scraper_run_log'
        managed = True
        ordering = ['-run_at']

    def __str__(self):
        return f'{self.run_at} ({self.status})'


class DLAScraperPendingOrganisationUpdate(models.Model):
    contract = models.ForeignKey("organisation.DLAContractLocation", verbose_name=_("Contract"), related_name="pending_updates_for_contract",
                                 on_delete=models.CASCADE)
    is_ipa = models.BooleanField(_("Is an IPA?"), default=False)
    current_organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Current organisation"),
                                             related_name="pending_updates_where_current", on_delete=models.CASCADE,
                                             null=True)
    proposed_organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Proposed organisation"),
                                              related_name="pending_updates_where_proposed", on_delete=models.CASCADE,
                                              null=True)
    ignored = models.BooleanField(_("Ignored?"), default=False)
    applied = models.BooleanField(_("Applied?"), default=False)

    class Meta:
        db_table = 'organisations_dla_pending_organisation_updates'
        managed = True
        ordering = ['id']

    def __str__(self):
        return f'{self.pk}'