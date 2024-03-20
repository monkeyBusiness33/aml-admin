from django.db import models
from django.utils.translation import gettext_lazy as _


class FuelPricingMarketIpaNameAlias(models.Model):
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 related_name="fuel_pricing_market_name_aliases_at_location", on_delete=models.CASCADE)
    name = models.CharField(_("IPA Name"), max_length=500)
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            related_name="fuel_pricing_market_name_aliases", on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"), on_delete=models.RESTRICT)

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_ipa_name_aliases'


class FuelPricingMarketCsvImporterNoteField(models.Model):
    note_str = models.CharField(_("Relevant Phrase from CSV Note"), max_length=500)
    field_name = models.CharField(_("DB Field Name"), max_length=100)
    field_value = models.BigIntegerField(_("DB Field Value"))

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_csv_importer_note_fields'
