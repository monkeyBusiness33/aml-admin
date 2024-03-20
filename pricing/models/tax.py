from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.postgres.aggregates import BoolOr
from django.db import models
from django.db.models import BooleanField, Case, CharField, F, IntegerField, Max, Q, Value, When
from django.db.models.functions import Concat
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import PricingUnit
from core.templatetags.currency_uom_tags import custom_round_to_str
from core.utils.datatables_functions import get_datatable_text_with_tooltip
from pricing.mixins import PricingCalculationMixin
from pricing.utils import check_band


class Tax(models.Model):
    applicable_country = models.ForeignKey("core.Country",
                                           verbose_name=_("Applicable Country"),
                                           null=True,
                                           on_delete=models.CASCADE,
                                           related_name='taxes')
    applicable_region = models.ForeignKey("core.Region",
                                          verbose_name=_("Applicable Region"),
                                          null=True,
                                          on_delete=models.CASCADE)
    local_name = models.CharField(_("Name"), max_length=100)
    short_name = models.CharField(_("Short Name"), max_length=50,
                                  null=True, blank=True)
    category = models.ForeignKey("pricing.TaxCategory",
                                 verbose_name=_("Category"),
                                 on_delete=models.CASCADE)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.CASCADE)
    verified_by_ads = models.BooleanField(_("Verified by ADS?"), default=False)

    class Meta:
        db_table = 'taxes'

    def __str__(self):
        return self.local_name


class TaxSource(models.Model):
    name = models.CharField(_("Name"), max_length=500)
    file_url = models.URLField(_("File URL"), max_length=500, null=True, blank=True)
    web_url = models.URLField(_("Web URL"), max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'taxes_sources'

    def __str__(self):
        return self.name


class TaxCategory(models.Model):
    name = models.CharField(_("Name"), max_length=100)

    class Meta:
        db_table = 'taxes_categories'

    def __str__(self):
        return self.name


class TaxRate(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'taxes_rates'

    def __str__(self):
        return self.name


class TaxRatePercentage(models.Model):
    tax = models.ForeignKey("pricing.Tax", verbose_name=_("Tax"),
                            related_name='rates', on_delete=models.CASCADE)
    tax_rate = models.ForeignKey("pricing.TaxRate", verbose_name=_("Rate"),
                                 on_delete=models.CASCADE)
    tax_percentage = models.DecimalField(_("Tax Percentage"), max_digits=6, decimal_places=4)

    class Meta:
        db_table = 'taxes_rates_percentages'

    def __str__(self):
        return f'{self.pk}'


class TaxFixedCostApplicationMethod(models.Model):
    name_override = models.CharField(_("Name"), max_length=100, null=True, blank=True)
    charge_structures_properties = models.ForeignKey("pricing.ChargeStructureProperties",
                                                     verbose_name=_("Charge Structures Properties"),
                                                     null=True, blank=True,
                                                     on_delete=models.CASCADE)

    class Meta:
        db_table = 'taxes_fixed_cost_application_methods'

    def __str__(self):
        return f'{self.pk}'

    @property
    def description(self):
        return f'{self.name_override}'


class TaxApplicationMethod(models.Model):
    fuel_pricing_unit = models.ForeignKey("core.PricingUnit",
                                          verbose_name=_("Fuel Pricing Unit"),
                                          null=True, blank=True,
                                          on_delete=models.CASCADE)
    fixed_cost_application_method = models.ForeignKey("pricing.TaxFixedCostApplicationMethod",
                                                      verbose_name=_("Fixed Cost Application Method"),
                                                      null=True, blank=True,
                                                      on_delete=models.CASCADE)

    class Meta:
        db_table = 'taxes_application_methods'

    def __str__(self):
        return f'{self.pk}'


class TaxRuleManager(models.Manager):
    def all_taxes(self, country):
        return self.filter(Q(tax__applicable_country=country) |
                             Q(tax__applicable_region__country=country) |
                             Q(tax_rate_percentage__tax__applicable_country=country) |
                             Q(tax_rate_percentage__tax__applicable_region__country=country))

    def country_taxes(self, country):
        return self.filter(Q(tax__applicable_country=country) |
                           Q(tax_rate_percentage__tax__applicable_country=country))

    def regional_taxes(self, country):
        return self.filter(Q(tax__applicable_region__country=country) |
                           Q(tax_rate_percentage__tax__applicable_region__country=country))


class TaxApplicationQuerySet(models.query.QuerySet):
    def applies_for_fuel_taken(self, is_fuel_taken):
        """
        If calculation involves no fuel uplift, we are not able to calculate
        any fuel-based taxes, so these have to be excluded.
        """
        if not is_fuel_taken:
            return self.filter(tax_application_method__fuel_pricing_unit__isnull=True)
        else:
            return self

    def applies_on_date(self, validity_date):
        return self.filter(
            Q(valid_from__lte=validity_date) & (Q(valid_to__gte=validity_date) | Q(valid_ufn=True))
        )

    def applies_to_commercial_private(self, is_private):
        if is_private:
            return self.filter(applies_to_private=True)
        else:
            return self.filter(applies_to_commercial=True)

    def applies_to_commercial_private_overlap(self, is_commercial, is_private):
        qs = self

        if not is_commercial:
            qs = qs.exclude(applies_to_commercial=True, applies_to_private=False)

        if not is_private:
            qs = qs.exclude(applies_to_commercial=False, applies_to_private=True)

        return qs

    def applies_to_current_org(self, current_org):
        return self.filter(
            Q(exception_only_for_organisation_id__isnull=True)
            | Q(exception_only_for_organisation_id=current_org.pk)
        )

    def applies_to_destination(self, applicable_destinations):
        return self.filter(
            Q(geographic_flight_type__in=applicable_destinations)
        )

    def applies_to_flight_type(self, applicable_flight_types):
        return self.filter(
            Q(applicable_flight_type__in=applicable_flight_types)
        )

    def applies_to_fuel_cat(self, fuel_cat):
        return self.filter(
            (Q(specific_fuel__isnull=True) | Q(specific_fuel__category=fuel_cat))
            & (Q(specific_fuel_cat__isnull=True) | Q(specific_fuel_cat=fuel_cat))
        )

    def applies_to_fuel_or_fees(self):
        return self.filter(
            Q(applies_to_fuel=True) | Q(applies_to_fees=True)
        )

    def applies_to_fuel_type(self, fuel_type):
        return self.filter(
            Q(specific_fuel__isnull=True) | Q(specific_fuel=fuel_type)
        )

    def distinct_per_location_and_category(self):
        return self.annotate(
            category_name = Case(
                When(Q(tax__isnull=True), then=F('tax_rate_percentage__tax__category__name')),
                default=F('tax__category__name')
            ),
            applicable_region_code = Case(
                When(Q(tax__isnull=True), then=F('tax_rate_percentage__tax__applicable_region__code')),
                default=F('tax__applicable_region__code')
            ),
            applicable_region_name = Case(
                When(Q(tax__isnull=True), then=F('tax_rate_percentage__tax__applicable_region__name')),
                default=F('tax__applicable_region__name')
            ),
        ).values(
            'category_name', 'applicable_region_code', 'applicable_region_name',
            'specific_airport__airport_details__icao_code'
        ).annotate(
            any_applies_to_fees=BoolOr('applies_to_fees'),
            any_applies_to_fuel=BoolOr('applies_to_fuel'),
            latest_update=Max('updated_at')
        )

    def filter_by_date_for_calc(self, validity_date_utc):
        """
        This filter needs to include valid and expired taxes (to use in case no valid pricing is present).
        We are always excluding future entries.
        """
        return self.annotate(
            expiry_date=F("valid_to"),
            is_expired=Case(
                When(Q(valid_to__lt=validity_date_utc),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(Q(valid_from__lte=validity_date_utc))


class TaxRuleQuerySet(TaxApplicationQuerySet):
    def applies_at_location(self, airport):
        return self.exclude(
            (Q(specific_airport_id__isnull=False) & ~Q(specific_airport_id=airport.pk)) |
            (Q(tax__applicable_country__isnull=False) & ~Q(
                tax__applicable_country_id=airport.details.country.pk)) |
            (Q(tax_rate_percentage__isnull=False) &
             (Q(tax_rate_percentage__tax__applicable_country__isnull=False) &
              ~Q(tax_rate_percentage__tax__applicable_country_id=airport.details.country.pk)) |
             (Q(tax_rate_percentage__tax__applicable_region__isnull=False) &
              ~Q(tax_rate_percentage__tax__applicable_region_id=airport.airport_details.region.pk))
             ) |
            (Q(tax__isnull=False) &
             (Q(tax__applicable_country__isnull=False) &
              ~Q(tax__applicable_country_id=airport.details.country.pk)) |
             (Q(tax__applicable_region__isnull=False) &
              ~Q(tax__applicable_region_id=airport.airport_details.region.pk))
             )
        )

    def with_details(self):
        return self.annotate(
            source=Value('official'),
            parent_tax=Case(
                When(Q(tax_rate_percentage__isnull=False), then=F('tax_rate_percentage__tax')),
                default=F('tax')
            ),
            tax_name=Case(
                When(Q(tax_rate_percentage__isnull=False), then=Case(
                    When(Q(tax_rate_percentage__tax__short_name__isnull=False), then=Concat(
                        F('tax_rate_percentage__tax__local_name'),
                        Value(' ('),
                        F('tax_rate_percentage__tax__short_name'),
                        Value(')'),
                        output_field=CharField()
                    )), default=F('tax_rate_percentage__tax__local_name'))
                     ), default=Case(
                    When(Q(tax__short_name__isnull=False), then=Concat(
                        F('tax__local_name'),
                        Value(' ('),
                        F('tax__short_name'),
                        Value(')'),
                        output_field=CharField()
                    )), default=F('tax__local_name')
                )
            )
        )

    def with_specificity_score(self):
        """
        Annotate specificity score for each applicable rule / exception, that will be used to determine the rate used
        after all filters are applied (rule with the highest score, which generally means more specific, wins).
        This is based on the similar solution used in the APC for taxes.
        Supplier and official taxes are considered separately (and compared), so that level is excluded.
        - Level 1: airport-specific: 2000 > region-specific: 1000 > country-specific: 0
        - Level 2: with specific flight type: 100, else: 0
        - Level 3: with specific destination: 10, else: 0
        - Level 4: Tax Rate: 9-(rateId), undefined: 9
        """
        return self.annotate(
            specificity_score=Case(
                When(Q(specific_airport__isnull=False), then=2000),
                When(Q(tax__applicable_region__isnull=False), then=1000),
                default = 0
            ) + Case(
                When(~Q(applicable_flight_type='A'), then=100), default=0
            ) + Case(
                When(~Q(geographic_flight_type='ALL'), then=10), default=0
            ) + Case(
                When(Q(tax_rate_percentage__isnull=False),
                     then=(9 - F('tax_rate_percentage__tax_rate_id'))),
                default=9
            )
        )


class TaxExceptionQuerySet(TaxApplicationQuerySet):
    def applies_at_location(self, airport):
        return self.exclude(
            (Q(exception_airport_id__isnull=False) & ~Q(exception_airport_id=airport.pk)) |
            (Q(exception_country_id__isnull=False) & ~Q(exception_country_id=airport.details.country.pk)) |
            ~Q(tax__applicable_country_id=airport.details.country.pk)
        )

    def filter_by_source_doc(self, used_plds, used_agreement_ids):
        return self.filter(
            (Q(source_agreement__isnull=True) | Q(source_agreement__pk__in=used_agreement_ids)) &
            (Q(related_pld__isnull=True) | Q(related_pld__pk__in=used_plds))
        )

    def with_details(self):
        return self.annotate(
            source=Value('supplier'),
            tax_name=Case(
                When(Q(tax__short_name__isnull=False), then=Concat(
                    F('tax__local_name'),
                    Value(' ('),
                    F('tax__short_name'),
                    Value(')'),
                    output_field=CharField()
                )), default=F('tax__local_name')
            ),
            operated_as_status=Case(
                When(Q(applies_to_commercial=True) & Q(applies_to_private=True), then=2),
                When(applies_to_commercial=True, then=1),
                When(applies_to_private=True, then=3),
                default=0,
                output_field=IntegerField()
            ),
        )

    def with_specificity_score(self):
        """
        Annotate specificity score for each applicable rule / exception, that will be used to determine the rate used
        after all filters are applied (rule with the highest score, which generally means more specific, wins).
        This is based on the similar solution used in the APC for taxes.
        Supplier and official taxes are considered separately (and compared), so that level is excluded.
        - Level 1: exception-only-for-organisation: 100000, else: 0
        - Level 2: airport-specific: 2000, country-specific: 0
        - Level 3: with specific flight type: 100, else: 0
        - Level 4: with specific destination: 10, else: 0
        - Level 5: Tax Rate: 9-(rateId), undefined: 9 (Here always 9)
        """
        return self.annotate(
            specificity_score=Case(
                When(Q(exception_only_for_organisation__isnull=False), then=100000), default=0
            ) + Case(
                When(Q(exception_airport__isnull=False), then=2000),
                default = 0
            ) + Case(
                When(~Q(applicable_flight_type='A'), then=100), default=0
            ) + Case(
                When(~Q(geographic_flight_type='ALL'), then=10), default=0
            ) + 9
        )


class TaxRule(models.Model, PricingCalculationMixin):
    tax_source = models.ForeignKey("pricing.TaxSource", verbose_name=_("Tax Source"),
                                   null=True, blank=True,
                                   related_name='tax_rules', on_delete=models.CASCADE)
    specific_airport = models.ForeignKey("organisation.Organisation",
                                         verbose_name=_("Specific Airport"),
                                         null=True, blank=True,
                                         limit_choices_to={'details__type_id': 8,
                                                           'airport_details__isnull': False},
                                         related_name='tax_rules',
                                         on_delete=models.CASCADE)
    tax = models.ForeignKey("pricing.Tax", verbose_name=_("Tax"), on_delete=models.CASCADE, null=True, related_name='tax_rule_set')
    applies_to_fuel = models.BooleanField(_("Applies to Fuel"), default=False)
    applies_to_services = models.BooleanField(_("Applies to Services"), default=False)
    applies_to_fees = models.BooleanField(_("Applies to Fees"), null=True, default=False)
    specific_fuel = models.ForeignKey("core.FuelType", verbose_name=_("Specific Fuel"),
                                      null=True, blank=True,
                                      on_delete=models.RESTRICT)
    specific_fuel_cat = models.ForeignKey("core.FuelCategory", verbose_name=_("Specific Fuel Category"),
                                          null=True, blank=True,
                                          on_delete=models.RESTRICT)
    specific_service = models.ForeignKey("pricing.ChargeService", verbose_name=_("Specific Service"),
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    specific_fee_category = models.ForeignKey("pricing.FuelFeeCategory", verbose_name=_("Specific Fee Category"),
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    applicable_flight_type = models.ForeignKey("core.FlightType",
                                               verbose_name=_("Flight Type"),
                                               db_column='applicable_flight_type_code',
                                               on_delete=models.CASCADE)
    geographic_flight_type = models.ForeignKey("core.GeographichFlightType",
                                               verbose_name=_("Geographic Flight Type"),
                                               db_column='geographic_flight_type_code',
                                               on_delete=models.CASCADE)
    band_1_type = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 1 Type"),
                                    null=True, blank=True,
                                    related_name='tax_rules_band_1',
                                    on_delete=models.CASCADE)
    band_1_start = models.DecimalField(_("Band 1 Start"), max_digits=10, decimal_places=4, null=True, blank=True)
    band_1_end = models.DecimalField(_("Band 1 End"), max_digits=10, decimal_places=4, null=True, blank=True)
    band_2_type = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 2 Type"),
                                    null=True, blank=True,
                                    related_name='tax_rules_band_2',
                                    on_delete=models.CASCADE)
    band_2_start = models.DecimalField(_("Band 2 Start"), max_digits=10, decimal_places=4, null=True, blank=True)
    band_2_end = models.DecimalField(_("Band 2 End"), max_digits=10, decimal_places=4, null=True, blank=True)
    tax_rate_percentage = models.ForeignKey("pricing.TaxRatePercentage", verbose_name=_("Tax Rate Percentage"),
                                            null=True, on_delete=models.CASCADE, related_name='tax_rules')
    tax_unit_rate = models.DecimalField(_("Tax Unit Rate"), max_digits=9, decimal_places=4, null=True, blank=True)
    tax_application_method = models.ForeignKey("pricing.TaxApplicationMethod",
                                               verbose_name=_("Tax Application Method"),
                                               related_name='applied_to_rules',
                                               null=True, blank=True,
                                               on_delete=models.CASCADE)
    valid_from = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False, null=True, blank=True)
    valid_ufn = models.BooleanField(_("Valid UFN"), default=False)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"), on_delete=models.CASCADE)
    taxable_tax = models.ForeignKey("pricing.TaxRule", verbose_name=_("Taxable Tax"),
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    waived_for_tech_stop = models.BooleanField(_("Waived For Tech Stop"), default=False)
    pax_must_stay_aboard = models.BooleanField(_("Pax Must Stay Aboard"), default=False)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=False)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True)
    parent_entry = models.ForeignKey("TaxRule", on_delete=models.SET_NULL, null=True, related_name='child_entries')
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    exemption_available_with_cert = models.BooleanField(_("Exemption Available with Certificate?"), default=False)


    objects = TaxRuleManager.from_queryset(TaxRuleQuerySet)()

    class Meta:
        db_table = 'taxes_rules'

    def save(self, *args, **kwargs):
        self.applies_to_services = self.applies_to_fees
        super(TaxRule, self).save(*args, **kwargs)

        return self


    def __str__(self):
        return f'{self.pk}'

    @property
    def application_method(self):
        """
        Returns the application method for non-percentage based rules.
        """
        if self.tax_application_method:
            return (self.tax_application_method.fuel_pricing_unit \
                    or self.tax_application_method.fixed_cost_application_method)

    @property
    def band_1_string(self):
        if self.band_1_type is not None:
            return f'{self.band_1_start} - {self.band_1_end}'

    @property
    def band_2_string(self):
        if self.band_2_type is not None:
            return f'{self.band_2_start} - {self.band_2_end}'

    @property
    def currency(self):
        if isinstance(self.application_method, PricingUnit):
            return self.application_method.currency

    @property
    def parent_tax_obj(self):
        if self.tax_rate_percentage is not None:
            return self.tax_rate_percentage.tax
        else:
            return self.tax

    @property
    def percentage(self):
        return getattr(self.tax_rate_percentage, 'tax_percentage', None)

    @property
    def tax_rate_string(self):
        if self.tax_application_method:
            if self.tax_application_method.fixed_cost_application_method:
                tax = self.tax_rate_percentage.tax if self.tax_rate_percentage else self.tax
                currency = tax.applicable_region.country.currency.code if tax.applicable_region \
                    else tax.applicable_country.currency.code

                return f'{self.tax_unit_rate} {currency} {self.tax_application_method.fixed_cost_application_method.name_override}'
            else:
                return f'{self.tax_unit_rate} {self.tax_application_method.fuel_pricing_unit.description}'
        else:
            if self.tax_rate_percentage:
                return f'{self.tax_rate_percentage.tax_percentage}%'
            else:
                return f'{self.tax_percentage}%'

    @property
    def get_tax_type(self):
        if self.specific_airport:
            return 'airport'

        elif getattr(self, 'tax_rate_percentage') is not None:
            if self.tax_rate_percentage.tax.applicable_region:
                return 'region'
            else:
                return 'country'

        elif getattr(self, 'tax') is not None:
            if self.tax.applicable_region:
                return 'region'
            else:
                return 'country'

    @property
    def get_tax_country(self):
        if getattr(self, 'tax_rate_percentage') is not None:
            if self.tax_rate_percentage.tax.applicable_region:
                return self.tax_rate_percentage.tax.applicable_region.country.id
            else:
                return self.tax_rate_percentage.tax.applicable_country.id

        elif getattr(self, 'tax') is not None:
            if self.tax.applicable_region:
                return self.tax.applicable_region.country.id
            else:
                return self.tax.applicable_country.id

    @property
    def get_tax_representation(self):
        if getattr(self, 'tax_rate_percentage') is not None:
            name = self.tax_rate_percentage.tax.local_name
            category = self.tax_rate_percentage.tax.category
        else:
            name = self.tax.local_name
            category = self.tax.category

        valid_to = self.valid_to if self.valid_to is not None else 'UFN'

        return f'{name} - {category} - {self.valid_from} - {valid_to}'

    @property
    def taxable(self):
        return self.taxable_tax

    def check_bands(self, uplift_scenario, fuel_type):
        '''
        Due to uplift quantity being specified to 4 decimal places, we need to ensure
        that there are no gaps when checking FU bands, which have resolution from int to 4 decimals,
        so we extend the band end to the next band start minus 0.0001 (if next band exists).
        '''
        if self.band_1_type and self.band_1_type.type == 'FU' and self.band_1_end:
            next_band_1_start = None

            if self.parent_entry:
                next_band_1_start = self.parent_entry.child_entries \
                    .filter(band_1_start__gt=self.band_1_end) \
                    .order_by('band_1_start').values_list('band_1_start', flat=True).first()
            elif self.child_entries.exists():
                next_band_1_start = self.child_entries \
                    .filter(band_1_start__gt=self.band_1_end) \
                    .order_by('band_1_start').values_list('band_1_start', flat=True).first()

            # Only extend if there is no gap larger than 1 between bands
            # (we have validation to prevent this now, but we can check it
            # just in case gaps are permissible in the future.)
            if next_band_1_start and next_band_1_start - self.band_1_end <= 1:
                self.band_1_end = Decimal(next_band_1_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        if self.band_2_type and self.band_2_type.type == 'FU' and self.band_2_end:
            next_band_2_start = None

            if self.parent_entry:
                next_band_2_start = self.parent_entry.child_entries \
                    .filter(band_2_start__gt=self.band_2_end) \
                    .order_by('band_2_start').values_list('band_2_start', flat=True).first()
            elif self.child_entries.exists():
                next_band_2_start = self.child_entries \
                    .filter(band_2_start__gt=self.band_2_end) \
                    .order_by('band_2_start').values_list('band_2_start', flat=True).first()

            # Only extend if there is no gap larger than 1 between bands
            # (we have validation to prevent this now, but we can check it
            # just in case gaps are permissible in the future.)
            if next_band_2_start and next_band_2_start - self.band_2_end <= 1:
                self.band_2_end = Decimal(next_band_2_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        bands_apply = check_band(uplift_scenario, fuel_type, self.band_1_type, self.band_1_start, self.band_1_end) and \
                      check_band(uplift_scenario, fuel_type, self.band_2_type, self.band_2_start, self.band_2_end)

        return bands_apply

    def get_rate_datatable_str(self, inc_rate_type=False, for_subtable=False):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        if self.tax_unit_rate is not None:
            formatted_discount = '{:.2f}'.format(self.tax_unit_rate)

            if Decimal(formatted_discount) != self.tax_unit_rate:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount} {self.application_method.description}',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.tax_unit_rate, 2, 6, normalize_decimals=True)}'
                                 f' {self.application_method.description}',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f' {self.application_method.description}'
        else:
            formatted_discount = '{:.2f}'.format(self.percentage)

            if Decimal(formatted_discount) != self.percentage:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount}%',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.percentage, 2, 6, normalize_decimals=True)}%',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f'%'

            if inc_rate_type:
                separator = ' ' if for_subtable else '<br>'
                formatted_discount += f'{separator}{self.tax_rate_percentage.tax_rate.name}'

        return formatted_discount


class TaxRuleException(models.Model, PricingCalculationMixin):
    tax_source = models.ForeignKey("pricing.TaxSource", verbose_name=_("Tax Source"),
                                   null=True, blank=True,
                                   related_name='tax_rules_exceptions', on_delete=models.CASCADE)
    exception_organisation = models.ForeignKey("organisation.Organisation",
                                               verbose_name=_("Exception Organisation"),
                                               on_delete=models.CASCADE)
    exception_country = models.ForeignKey("core.Country", verbose_name=_("Country"),
                                          null=True, blank=True, on_delete=models.RESTRICT)
    exception_airport = models.ForeignKey("organisation.Organisation",
                                          verbose_name=_("Specific Airport"),
                                          null=True, blank=True,
                                          limit_choices_to={'details__type_id': 8,
                                                            'airport_details__isnull': False},
                                          related_name='tax_rules_exceptions',
                                          on_delete=models.CASCADE)
    tax = models.ForeignKey("pricing.Tax", verbose_name=_("Tax"), on_delete=models.CASCADE)
    applies_to_fuel = models.BooleanField(_("Applies to Fuel"), default=False)
    applies_to_services = models.BooleanField(_("Applies to Services"), default=False)
    applies_to_fees = models.BooleanField(_("Applies to Fees"), null=True, default=False)
    specific_fuel = models.ForeignKey("core.FuelType", verbose_name=_("Specific Fuel"),
                                      null=True, blank=True,
                                      on_delete=models.RESTRICT)
    specific_fuel_cat = models.ForeignKey("core.FuelCategory", verbose_name=_("Specific Fuel Category"),
                                          null=True, blank=True,
                                          on_delete=models.RESTRICT)
    specific_service = models.ForeignKey("pricing.ChargeService", verbose_name=_("Specific Service"),
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    specific_fee_category = models.ForeignKey("pricing.FuelFeeCategory", verbose_name=_("Specific Fee Category"),
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    applicable_flight_type = models.ForeignKey("core.FlightType",
                                               verbose_name=_("Flight Type"),
                                               db_column='applicable_flight_type_code',
                                               on_delete=models.CASCADE)
    geographic_flight_type = models.ForeignKey("core.GeographichFlightType",
                                               verbose_name=_("Geographich Flight Type"),
                                               db_column='geographic_flight_type_code',
                                               on_delete=models.CASCADE)
    band_1_type = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 1 Type"),
                                    null=True, blank=True,
                                    related_name='tax_rules_exceptions_band_1',
                                    on_delete=models.CASCADE)
    band_1_start = models.DecimalField(_("Band 1 Start"), max_digits=10, decimal_places=4,
                                       null=True, blank=True)
    band_1_end = models.DecimalField(_("Band 1 End"), max_digits=10, decimal_places=4,
                                     null=True, blank=True)
    band_2_type = models.ForeignKey("pricing.ChargeBand", verbose_name=_("Band 2 Type"),
                                    null=True, blank=True,
                                    related_name='tax_rules_exceptions_band_2',
                                    on_delete=models.CASCADE)
    band_2_start = models.DecimalField(_("Band 2 Start"), max_digits=10, decimal_places=4,
                                       null=True, blank=True)
    band_2_end = models.DecimalField(_("Band 2 End"), max_digits=10, decimal_places=4,
                                     null=True, blank=True)
    tax_percentage = models.DecimalField(_("Tax Percentage"), max_digits=6, decimal_places=4,
                                         null=True, blank=True)
    tax_unit_rate = models.DecimalField(_("Tax Unit Rate"), max_digits=9, decimal_places=4,
                                        null=True, blank=True)
    tax_application_method = models.ForeignKey("pricing.TaxApplicationMethod",
                                               verbose_name=_("Tax Application Method"),
                                               null=True, blank=True,
                                               on_delete=models.CASCADE)
    valid_from = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False, null=True, blank=True)
    valid_ufn = models.BooleanField(_("Valid UFN"), default=False)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"), on_delete=models.CASCADE)
    exception_only_for_organisation = models.ForeignKey("organisation.Organisation",
                                                        verbose_name=_("Exception only for Organisations"),
                                                        null=True, blank=True,
                                                        related_name='organisation_specific_tax_exceptions',
                                                        on_delete=models.CASCADE)
    taxable_exception = models.ForeignKey("pricing.TaxRuleException", verbose_name=_("Taxable Exception"),
                                    null=True, blank=True,
                                    on_delete=models.CASCADE, related_name="taxable_exception_for")
    taxable_tax = models.ForeignKey("pricing.TaxRule", verbose_name=_("Taxable Tax"),
                                    null=True, on_delete=models.CASCADE, related_name="taxable_tax_for")
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True)
    waived_for_tech_stop = models.BooleanField(_("Waived For Tech Stop"), default=False)
    pax_must_stay_aboard = models.BooleanField(_("Pax Must Stay Aboard"), default=False)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=False)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)

    parent_entry = models.ForeignKey("TaxRuleException", on_delete=models.SET_NULL, null=True, related_name='child_entries')
    related_pld = models.ForeignKey('pricing.FuelPricingMarketPld', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="associated_tax_exceptions")
    source_agreement = models.ForeignKey('supplier.FuelAgreement', on_delete=models.CASCADE, null=True, blank=True,
                                         related_name='associated_tax_exceptions')
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    exemption_available_with_cert = models.BooleanField(_("Exemption Available with Certificate?"), default=False)

    objects = TaxExceptionQuerySet.as_manager()

    class Meta:
        db_table = 'taxes_rules_exceptions'

    def save(self, *args, **kwargs):
        self.applies_to_services = self.applies_to_fees
        super(TaxRuleException, self).save(*args, **kwargs)

        return self

    def __str__(self):
        return f'{self.pk}'

    @property
    def application_method(self):
        """
        Returns the application method for non-percentage based exceptions.
        """
        if self.tax_application_method:
            return (self.tax_application_method.fuel_pricing_unit \
                    or self.tax_application_method.fixed_cost_application_method)

    @property
    def band_1_string(self):
        if self.band_1_type is not None:
            return f'{round(self.band_1_start, 2)} - {round(self.band_1_end, 2)}'

    @property
    def band_2_string(self):
        if self.band_2_type is not None:
            return f'{round(self.band_2_start, 2)} - {round(self.band_2_end, 2)}'

    @property
    def currency(self):
        if isinstance(self.application_method, PricingUnit):
            return self.application_method.currency

    @property
    def details_url(self):
        if self.source_agreement is not None:
            return reverse_lazy('admin:agreement_supplier_tax_details', kwargs={
                'agreement_pk': self.source_agreement_id,
                'pk': self.pk
            })
        elif self.related_pld is not None:
            return reverse_lazy('admin:fuel_pricing_market_documents_supplier_defined_tax_details', kwargs={
                'pld': self.related_pld_id,
                'pk': self.pk
            })

    @property
    def is_historical(self):
        if self.source_agreement is not None:
            return self.valid_to and self.valid_to < datetime.now(timezone.utc).date() \
                or self.source_agreement.end_date and self.source_agreement.end_date < datetime.now(timezone.utc)
        else:
            return self.related_pld.is_current

    @property
    def operated_as(self):
        if self.applies_to_commercial and self.applies_to_private:
            return 'Commercial, Private'
        elif self.applies_to_commercial:
            return 'Commercial'
        elif self.applies_to_private:
            return 'Private'

    @property
    def percentage(self):
        return self.tax_percentage

    @property
    def source_doc_name(self):
        if self.source_agreement is not None:
            return str(self.source_agreement)
        elif self.related_pld is not None:
            return self.related_pld.pld_name

    @property
    def tax_rate_string(self):
        if self.tax_application_method:
            if self.tax_application_method.fixed_cost_application_method:
                tax = self.tax_rate_percentage.tax if hasattr(self, 'tax_rate_percentage') else self.tax
                currency = tax.applicable_region.country.currency.code if tax.applicable_region \
                    else tax.applicable_country.currency.code

                return f'{self.tax_unit_rate} {currency} {self.tax_application_method.fixed_cost_application_method.name_override}'
            else:
                return f'{self.tax_unit_rate} {self.tax_application_method.fuel_pricing_unit.description}'
        else:
            return f'{self.tax_percentage}%'

    @property
    def get_tax_representation(self):

        name = self.tax.local_name
        category = self.tax.category
        valid_to = self.valid_to if self.valid_to is not None else f'UFN'

        return f'{name} - {category} - {self.valid_from} - {valid_to}'

    @property
    def taxable(self):
        return self.taxable_exception or self.taxable_tax

    def check_bands(self, uplift_scenario, fuel_type):
        '''
        Due to uplift quantity being specified to 4 decimal places, we need to ensure
        that there are no gaps when checking FU bands, which have resolution from int to 4 decimals,
        so we extend the band end to the next band start minus 0.0001 (if next band exists).
        '''
        if self.band_1_type and self.band_1_type.type == 'FU' and self.band_1_end:
            next_band_1_start = None

            if self.parent_entry:
                next_band_1_start = self.parent_entry.child_entries \
                    .filter(band_1_start__gt=self.band_1_end) \
                    .order_by('band_1_start').values_list('band_1_start', flat=True).first()
            elif self.child_entries.exists():
                next_band_1_start = self.child_entries \
                    .filter(band_1_start__gt=self.band_1_end) \
                    .order_by('band_1_start').values_list('band_1_start', flat=True).first()

            # Only extend if there is no gap larger than 1 between bands
            # (we have validation to prevent this now, but we can check it
            # just in case gaps are permissible in the future.)
            if next_band_1_start and next_band_1_start - self.band_1_end <= 1:
                self.band_1_end = Decimal(next_band_1_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        if self.band_2_type and self.band_2_type.type == 'FU' and self.band_2_end:
            next_band_2_start = None

            if self.parent_entry:
                next_band_2_start = self.parent_entry.child_entries \
                    .filter(band_2_start__gt=self.band_2_end) \
                    .order_by('band_2_start').values_list('band_2_start', flat=True).first()
            elif self.child_entries.exists():
                next_band_2_start = self.child_entries \
                    .filter(band_2_start__gt=self.band_2_end) \
                    .order_by('band_2_start').values_list('band_2_start', flat=True).first()

            # Only extend if there is no gap larger than 1 between bands
            # (we have validation to prevent this now, but we can check it
            # just in case gaps are permissible in the future.)
            if next_band_2_start and next_band_2_start - self.band_2_end <= 1:
                self.band_2_end = Decimal(next_band_2_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        bands_apply = check_band(uplift_scenario, fuel_type, self.band_1_type, self.band_1_start, self.band_1_end) and \
                      check_band(uplift_scenario, fuel_type, self.band_2_type, self.band_2_start, self.band_2_end)

        return bands_apply

    def get_rate_datatable_str(self):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        if self.tax_unit_rate is not None:
            formatted_discount = '{:.2f}'.format(self.tax_unit_rate)

            if Decimal(formatted_discount) != self.tax_unit_rate:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount} {self.application_method.description}',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.tax_unit_rate, 2, 6, normalize_decimals=True)}'
                                 f' {self.application_method.description}',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f' {self.application_method.description}'
        else:
            formatted_discount = '{:.2f}'.format(self.tax_percentage)

            if Decimal(formatted_discount) != self.tax_percentage:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount}%',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.tax_percentage, 2, 6, normalize_decimals=True)}%',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f'%'

        return formatted_discount
