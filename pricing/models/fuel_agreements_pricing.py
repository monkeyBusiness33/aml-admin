import re
from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.db import models
from django.db.models import BooleanField, Case, CharField, Count, ExpressionWrapper, F, Func, IntegerField, Q, \
    Value, When
from django.db.models.functions import Concat
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from core.models.uom import UnitOfMeasurement
from core.templatetags.currency_uom_tags import custom_round_to_str
from core.utils.archivable_model_abstract import ArchivableModel, ArchivableModelManager, ArchivableModelQuerySet
from core.utils.custom_query_expressions import CommaSeparatedDecimal, CommaSeparatedDecimalOrInteger,\
    CommaSeparatedDecimalRoundTo2
from core.utils.datatables_functions import get_datatable_badge, get_datatable_text_with_tooltip
from organisation.models import Organisation
from user.models import Person
from .fuel_fees import SupplierFuelFeeRate
from ..models.tax import TaxRule, TaxRuleException
from ..utils import check_fuel_band_overlap, check_fuel_band
from pricing.mixins import PricingCalculationMixin
from supplier.models import FuelAgreement


class FuelAgreementPricing(ArchivableModel, PricingCalculationMixin):
    class Meta:
        abstract = True

    def archive(self, archived_by: Person=None):
        """
        Archive any additional child band rows. Update person and set price_active to False.
        """
        for row in self.child_entries.all():
            row.archive(archived_by)

        if archived_by:
            self.updated_by = archived_by

        self.price_active = False
        super().archive()


    @property
    def pricing_unit(self):
        if getattr(self, 'pricing_discount_amount', None) is not None:
            return self.pricing_discount_unit
        elif getattr(self, 'pricing_discount_percentage', None) is not None:
            return getattr(self.market_pricing_base, 'pricing_unit', None)
        elif getattr(self, 'differential_pricing_unit', None) is not None:
            return self.differential_pricing_unit

    def get_rate_unit_price(self):
        if getattr(self, 'pricing_discount_amount', None) is not None:
            return self.pricing_discount_amount
        elif getattr(self, 'pricing_discount_percentage', None) is not None:
            return self.market_pricing_base.get_rate_unit_price()
        elif getattr(self, 'differential_pricing_unit', None) is not None:
            return self.differential_value

    @property
    def uom(self):
        return getattr(self.pricing_unit, 'uom', None)

    @property
    def currency(self):
        return getattr(self.pricing_unit, 'currency', None)

    @property
    def operated_as(self):
        if self.applies_to_commercial and self.applies_to_private:
            return 'Commercial, Private'
        elif self.applies_to_commercial:
            return 'Commercial'
        elif self.applies_to_private:
            return 'Private'

    @property
    def supplier(self):
        return self.agreement.supplier

    @property
    def relevant_fuel_fees(self):
        '''
        Function that gets all entries from `suppliers_fuel_fees_rates`
        that are relevant to the given agreement pricing instance
        (with corresponding `suppliers_fuel_fees`)
        '''
        qs = SupplierFuelFeeRate.objects.with_details() \
            .filter_by_source_doc((), [self.agreement.pk]) \
            .applies_at_location(self.location) \
            .applies_to_fuel_type(self.fuel) \
            .applies_to_delivery_method(self.delivery_methods.all()) \
            .applies_to_commercial_private_overlap(self.applies_to_commercial, self.applies_to_private) \
            .exclude(deleted_at__isnull=False)

        # Here we can have generic 'all' on both ends, so we filter only if pricing demands it
        if self.destination_type.code != 'ALL':
            applicable_destinations = ['ALL', self.destination_type.code]
            qs = qs.applies_to_destination(applicable_destinations)

        if self.flight_type.code != 'A':
            applicable_flight_types = ['A'] + (['B', 'G'] if self.flight_type.code in ['B', 'G'] \
                                                   else [self.flight_type.code])

            qs = qs.applies_to_flight_type(applicable_flight_types)

        # If the selected pricing has IPA specified, filter by IPA
        if self.ipa_id is not None:
            qs = qs.filter(
                supplier_fuel_fee__ipa_id=self.ipa_id
            )

        # Sort the results
        qs = qs.order_by('supplier_fuel_fee__fuel_fee_category__name', 'supplier_fuel_fee__local_name',
                         'supplier_fuel_fee__supplier__details__registered_name',
                         'supplier_fuel_fee__ipa__details__registered_name', 'flight_type', 'destination_type',
                         'specific_fuel', 'delivery_method', 'quantity_band_start',
                         'weight_band_start')

        # Filter out any rates with non-overlapping quantity bands
        rates = [rate for rate in qs if check_fuel_band_overlap(self.band_uom, self.band_start, self.band_end,
                                                                rate.quantity_band_uom, rate.quantity_band_start,
                                                                rate.quantity_band_end, self.fuel)]

        fees = defaultdict(list)

        for rate in rates:
            fees[str(rate.supplier_fuel_fee_id)].append(rate)

        return dict(fees)

    @property
    def supplier_taxes(self):
        '''
        Function that filters out all entries from `taxes_rules_exceptions`
        that are relevant to the given agreement pricing instance
        '''
        qs = TaxRuleException.objects.with_details() \
            .filter_by_source_doc((), [self.agreement.pk]) \
            .applies_to_fuel_or_fees() \
            .applies_at_location(self.location) \
            .applies_to_fuel_type(self.fuel) \
            .applies_to_commercial_private_overlap(self.applies_to_commercial, self.applies_to_private) \
            .exclude(deleted_at__isnull=False)

        # Here we can have generic 'all' on both ends, so we filter only if pricing demands it
        if self.destination_type.code != 'ALL':
            applicable_destinations = ['ALL', self.destination_type.code]
            qs = qs.applies_to_destination(applicable_destinations)

        if self.flight_type.code != 'A':
            applicable_flight_types = ['A'] + (['B', 'G'] if self.flight_type.code in ['B', 'G'] \
                                                   else [self.flight_type.code])

            qs = qs.applies_to_flight_type(applicable_flight_types)

        # Annotate with tax source (supplier / official) and name
        qs = qs.annotate(
            source=Value('supplier'),
            tax_name=Case(
                When(Q(tax__short_name__isnull=False), then=Concat(
                    F('tax__local_name'),
                    Value(' ('),
                    F('tax__short_name'),
                    Value(')'),
                    output_field=CharField()
                )), default=F('tax__local_name')
            )
        )

        # Sort the results
        qs = qs.order_by('tax__category__name', 'applicable_flight_type', 'geographic_flight_type', 'specific_fuel',
                         'band_1_type__name', 'band_1_start', 'band_2_type__name', 'band_2_start',
                         '-tax_unit_rate', '-tax_percentage')

        # If either of the bands is of type 'FU', filter out any rows with non-overlapping quantity bands
        supplier_tax_exceptions = []

        for row in qs:
            if getattr(row.band_1_type, 'type', None) == 'FU':
                unit = re.search(r'\((.*)\)', row.band_1_type.name).groups()[0]
                unit_code = 'USG' if unit == 'usg' else 'L'
                uom = UnitOfMeasurement.objects.filter(code=unit_code).first()

                if check_fuel_band_overlap(self.band_uom, self.band_start, self.band_end, uom, row.band_1_start,
                                           row.band_1_end, self.fuel):
                    supplier_tax_exceptions.append(row)
            elif getattr(row.band_2_type, 'type', None) == 'FU':
                unit = re.search(r'\((.*)\)', row.band_2_type.name).groups()[0]
                unit_code = 'USG' if unit == 'usg' else 'L'
                uom = UnitOfMeasurement.objects.filter(code=unit_code).first()

                if check_fuel_band_overlap(self.band_uom, self.band_start, self.band_end, uom, row.band_2_start,
                                           row.band_2_end, self.fuel):
                    supplier_tax_exceptions.append(row)
            else:
                supplier_tax_exceptions.append(row)

        taxes = defaultdict(list)

        for rule in supplier_tax_exceptions:
            taxes[str(rule.tax_id)].append(rule)

        return dict(taxes)

    @property
    def official_taxes(self):
        '''
        Function that filters out all entries from `taxes_rules`
        that are relevant to the given agreement pricing instance
        '''

        qs = TaxRule.objects.with_details() \
            .applies_to_fuel_or_fees() \
            .applies_at_location(self.location) \
            .applies_to_fuel_type(self.fuel) \
            .applies_to_commercial_private_overlap(self.applies_to_commercial, self.applies_to_private) \
            .exclude(deleted_at__isnull=False)

        # Here we can have generic 'all' on both ends, so we filter only if pricing demands it
        if self.destination_type.code != 'ALL':
            applicable_destinations = ['ALL', self.destination_type.code]
            qs = qs.applies_to_destination(applicable_destinations)

        if self.flight_type.code != 'A':
            applicable_flight_types = ['A'] + (['B', 'G'] if self.flight_type.code in ['B', 'G'] \
                                                   else [self.flight_type.code])

            qs = qs.applies_to_flight_type(applicable_flight_types)

         # Annotate with tax, its source (supplier / official) and name
        qs = qs.annotate(
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

        # Sort the results
        qs = qs.order_by('tax__category__name', 'applicable_flight_type', 'geographic_flight_type', 'specific_fuel',
                         'tax_rate_percentage__tax_rate', 'band_1_type__name', 'band_1_start', 'band_2_type__name',
                         'band_2_start',
                         '-tax_unit_rate', '-tax_rate_percentage__tax_percentage')

        # If either of the bands is of type 'FU', filter out any rows with non-overlapping quantity bands
        official_tax_rules = []

        for row in qs:
            if getattr(row.band_1_type, 'type', None) == 'FU':
                unit = re.search(r'\((.*)\)', row.band_1_type.name).groups()[0]
                unit_code = 'USG' if unit == 'usg' else 'L'
                uom = UnitOfMeasurement.objects.filter(code=unit_code).first()

                if check_fuel_band_overlap(self.band_uom, self.band_start, self.band_end, uom, row.band_1_start,
                                           row.band_1_end, self.fuel):
                    official_tax_rules.append(row)
            elif getattr(row.band_2_type, 'type', None) == 'FU':
                unit = re.search(r'\((.*)\)', row.band_2_type.name).groups()[0]
                unit_code = 'USG' if unit == 'usg' else 'L'
                uom = UnitOfMeasurement.objects.filter(code=unit_code).first()

                if check_fuel_band_overlap(self.band_uom, self.band_start, self.band_end, uom, row.band_2_start,
                                           row.band_2_end, self.fuel):
                    official_tax_rules.append(row)
            else:
                official_tax_rules.append(row)

        taxes = defaultdict(list)

        for rule in official_tax_rules:
            taxes[str(rule.parent_tax)].append(rule)

        # For each tax, if airport-specific rules exist, drop the country-specific ones
        for tax in taxes:
            airport_specific_rules = list(filter(lambda x: x.specific_airport is not None, taxes[tax]))

            if len(airport_specific_rules):
                taxes[tax] = airport_specific_rules

        return dict(taxes)

    @property
    def relevant_taxes(self):
        '''
        Merge both types of taxes into a single dictionary
        '''
        supplier_taxes = self.supplier_taxes
        official_taxes = self.official_taxes

        taxes = set(supplier_taxes).union(official_taxes)
        return dict((t, supplier_taxes.get(t, list()) + official_taxes.get(t, list())) for t in taxes)

    @property
    def is_published(self):
        return self.agreement.is_published

    def check_band(self, uplift_qty, uplift_uom, fuel_type):
        '''
        Due to uplift quantity being specified to 4 decimal places, we need to ensure
        that there are no gaps when checking bands, which currently have int values,
        so we extend the band end to the next band start minus 0.0001 (if next band exists).
        '''
        next_band_start = None

        if self.parent_entry and self.band_end:
            next_band_start = self.parent_entry.child_entries \
                .filter(band_start__gt=self.band_end) \
                .order_by('band_start').values_list('band_start', flat=True).first()
        elif self.child_entries.exists() and self.band_end:
            next_band_start = self.child_entries \
                .filter(band_start__gt=self.band_end) \
                .order_by('band_start').values_list('band_start', flat=True).first()

        # Only extend if there is no gap larger than 1 between bands
        # (we have validation to prevent this now, but we can check it
        # just in case gaps are permissible in the future.)
        if next_band_start and next_band_start - self.band_end <= 1:
            self.band_end = Decimal(next_band_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        return check_fuel_band(self.band_uom, self.band_start, self.band_end,
                               uplift_qty, uplift_uom, fuel_type)

    def get_fuel_tax(self):
        if self.band_start is None or self.band_end is None:
            self.band_start = 0
            self.band_end = 0

        # Shouldn't be the case, as we don't allow setting both litre and us gallon bands for the same type of tax...
        # (at least for now)
        band_query = []
        if getattr(self.band_uom, 'description', lambda: 'No band') == 'Litre':
            band_query = [14]
        elif getattr(self.band_uom, 'description', lambda: 'No band') == 'US Gallon':
            band_query = [15]

        common_filters = Q(Q(applies_to_fuel=True),
                           Q(tax__applicable_country=self.location.details.country) |
                           Q(tax_rate_percentage__tax__applicable_country=self.location.details.country),
                           Q(specific_fuel=self.fuel) | Q(specific_fuel__isnull=True),
                           Q(valid_from__lte=self.agreement.start_date),
                           Q(Q(valid_to__gte=self.agreement.end_date.date()) | Q(valid_ufn=True)),
                           Q(Q(Q(band_1_type_id__in=band_query),
                               Q(band_1_start__lte=self.band_start), Q(band_1_end__gte=self.band_end)) |
                             Q(Q(band_2_type_id__in=band_query),
                               Q(band_2_start__lte=self.band_start), Q(band_2_end__gte=self.band_end)) |
                             Q(Q(band_1_type__isnull=True), Q(band_2_type__isnull=True))
                             ))

        if self.flight_type_id == 'A' and self.destination_type_id == 'ALL':
            qs = TaxRule.objects.filter(common_filters)\
                                .exclude(~Q(specific_airport = self.location),
                                          Q(specific_airport__isnull=False))\
                                .order_by('id')

            return qs

        elif self.flight_type_id == 'A':
            qs = TaxRule.objects.filter(common_filters,
                                        Q(geographic_flight_type = self.destination_type) |
                                        Q(geographic_flight_type_id = 'ALL'))\
                                .exclude(~Q(specific_airport = self.location),
                                          Q(specific_airport__isnull=False))\
                                .order_by('id')

            return qs

        elif  self.destination_type_id == 'ALL':
            qs = TaxRule.objects.filter(common_filters,
                                        Q(applicable_flight_type = self.flight_type) |
                                        Q(applicable_flight_type_id = 'A'))\
                                .exclude(~Q(specific_airport = self.location),
                                          Q(specific_airport__isnull=False))\
                                .order_by('id')

            return qs

        else:
            qs = TaxRule.objects.filter(common_filters,
                                        Q(applicable_flight_type = self.flight_type) |
                                        Q(applicable_flight_type_id = 'A'),
                                        Q(geographic_flight_type = self.destination_type) |
                                        Q(geographic_flight_type_id = 'ALL'))\
                                .exclude(~Q(specific_airport = self.location),
                                          Q(specific_airport__isnull=False))\
                                .order_by('id')

            return qs


class FuelAgreementPricingQueryset(ArchivableModelQuerySet):
    def active(self):
        return self.filter(Q(price_active=True))

    def applies_at_location(self, airport):
        return self.filter(Q(location=airport))

    def applies_to_apron(self, apron):
        if apron is not None:
            return self.filter(Q(specific_apron__isnull=True) | Q(specific_apron=apron))
        else:
            return self

    def applies_to_client(self, client):
        return self.filter(Q(client__isnull=True) | Q(client=client))

    def applies_to_commercial_private(self, is_private):
        if is_private:
            return self.filter(applies_to_private=True)
        else:
            return self.filter(applies_to_commercial=True)

    def applies_to_destination(self, applicable_destinations):
        return self.filter(
            Q(destination_type__in=applicable_destinations)
        )

    def applies_to_flight_type(self, applicable_flight_types):
        return self.filter(
            Q(flight_type__in=applicable_flight_types)
        )

    def applies_to_fuel_cat(self, fuel_cat):
        return self.filter(
            Q(fuel__isnull=True) | Q(fuel__category=fuel_cat)
        )

    def applies_to_fuel_type(self, fuel_type):
        return self.filter(
            Q(fuel__isnull=True) | Q(fuel=fuel_type)
        )

    def applies_to_fueling_method(self, is_overwing):
        if is_overwing:
            return self.filter(
                Q(specific_hookup_method__isnull=True) | Q(specific_hookup_method='OW')
            )
        else:
            return self.filter(
                Q(specific_hookup_method__isnull=True) | Q(specific_hookup_method='SP')
            )

    def applies_to_handler(self, handler):
        if handler is not None:
            return self.filter(Q(specific_handler__isnull=True) | Q(specific_handler=handler))
        else:
            return self

    def filter_by_date_for_calc(self, validity_datetime_utc, location, extend_expired):
        """
        This filter needs to include valid and expired pricing (to use in case no valid pricing is present).
        We are always excluding future pricing. Only include expired pricing if the relevant option is on.
        """
        qs = self.annotate(
            expiry_date=Case(
                When(Q(deleted_at__isnull=False),
                     then=Func(
                         F("deleted_at"),
                         Value('yyyy-MM-dd HH:MI'),
                         function='to_char',
                         output_field=CharField()
                     )),
                default=Func(
                    F("agreement__end_date"),
                    Value('yyyy-MM-dd HH:MI'),
                    function='to_char',
                    output_field=CharField()
                ),
                output_field=CharField()
            ),
            is_expired=Case(
                When(Q(agreement__end_date__lt=validity_datetime_utc) &
                     Q(agreement__valid_ufn=False) |
                     Q(deleted_at__lt=validity_datetime_utc),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(Q(agreement__start_date__lte=validity_datetime_utc))

        if not extend_expired:
            qs = qs.exclude(Q(is_expired=True))

        return qs

    def with_specificity_score(self):
        """
        Annotate specificity score for each applicable rate, that will be used to determine the rate used
        after all filters are applied (rate with the highest score, which generally means more specific, wins).
        This is based on the similar solution used in the APC for taxes.
        - Level 1: handler-specific: 1000, generic: 0
        - Level 2: with specific flight type: 100, else: 0
        - Level 3: with specific destination: 10, else: 0
        - Level 4: with specific hookup method: 1, else: 0
        """
        return self.annotate(
            specificity_score=Case(
                When(specific_handler__isnull=False, then=1000), default=0
            ) + Case(
                When(~Q(flight_type='A'), then=100), default=0
            ) + Case(
                When(~Q(destination_type='ALL'), then=10), default=0
            ) + Case(
                When(specific_hookup_method__isnull=False, then=1), default=0
            )
        )


class FuelAgreementPricingFormulaQuerySet(FuelAgreementPricingQueryset):
    def with_index_pricing_status(self, supplier_pk):
        today = date.today()

        from sql_util.utils import SubqueryCount

        return self.annotate(
            price_count=Count('pricing_index__prices'),
            valid_price_count=Count(Case(
                When(
                    Q(pricing_index__prices__valid_to__gte=today)
                    | Q(pricing_index__prices__valid_ufn=True), then=1),
                output_field=IntegerField(),
            )),
            published_valid_price_count=Count(Case(
                When((Q(pricing_index__prices__valid_to__gte=today) | Q(pricing_index__prices__valid_ufn=True))
                     & Q(pricing_index__prices__is_published=True), then=1),
                output_field=IntegerField(),
            )),
            index_pricing_status = Case(
                When(price_count=0, then=Value(3)),
                When(valid_price_count=0, then=Value(2)),
                When(published_valid_price_count=0, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
        )


class FuelAgreementPricingManualDeliveryMethods(models.Model):
    pricing = models.ForeignKey('FuelAgreementPricingManual', verbose_name=_("Formula Discount Pricing"),
                                on_delete=models.RESTRICT)
    delivery_method = models.ForeignKey("core.FuelEquipmentType", verbose_name=_("Delivery Method"),
                                        on_delete=models.RESTRICT)

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_manual_delivery_methods'


class FuelAgreementPricingManualWithDetailsManager(ArchivableModelManager):
    def with_details(self):
        return self.annotate(
            icao_iata=Case(
                When(Q(location__airport_details__iata_code__isnull=True)
                     | Q(location__airport_details__iata_code=''), then=F(
                    'location__airport_details__icao_code')),
                When(Q(location__airport_details__icao_code__isnull=True)
                     | Q(location__airport_details__icao_code=''), then=F(
                    'location__airport_details__iata_code')),
                default=Concat(
                    'location__airport_details__icao_code',
                    Value(' / '),
                    'location__airport_details__iata_code',
                    output_field=CharField()
                )
            ),
            ipa_name=Case(
                When(Q(ipa__details__registered_name__isnull=True)
                     | Q(ipa__details__registered_name=''), then=F(
                    'ipa__details__trading_name')),
                When(Q(ipa__details__trading_name__isnull=True)
                     | Q(ipa__details__trading_name=''), then=F(
                    'ipa__details__registered_name')),
                default=Concat(
                    'ipa__details__registered_name',
                    Value(' T/A '),
                    'ipa__details__trading_name',
                    output_field=CharField()
                )
            ),
            quantity_band=Case(
                When(Q(band_uom__isnull=False), then=Concat(
                    CommaSeparatedDecimalOrInteger(F('band_start')),
                    Value(' - '),
                    CommaSeparatedDecimalOrInteger(F('band_end')),
                    Value(' '),
                    F('band_uom__description_plural'),
                    output_field=CharField()
                ))
            ),
            specific_client=Case(
                When(Q(client__details__registered_name__isnull=True)
                     | Q(client__details__registered_name=''), then=F(
                    'client__details__trading_name')),
                When(Q(client__details__trading_name__isnull=True)
                     | Q(client__details__trading_name=''), then=F(
                    'client__details__registered_name')),
                default=Concat(
                    'client__details__registered_name',
                    Value(' T/A '),
                    'client__details__trading_name',
                    output_field=CharField()
                )
            ),
            discount_amount=Case(
                When(Q(pricing_discount_amount__isnull=False), then=Concat(
                    CommaSeparatedDecimal(F('pricing_discount_amount')),
                    Value(' '),
                    F('pricing_discount_unit__description_short'),
                    output_field=CharField()
                ))
            ),
            discount_amount_long=Case(
                When(Q(pricing_discount_amount__isnull=False), then=Concat(
                    CommaSeparatedDecimal(F('pricing_discount_amount')),
                    Value(' '),
                    F('pricing_discount_unit__description'),
                    output_field=CharField()
                ))
            ),
            discount_percentage=Case(
                When(Q(pricing_discount_percentage__isnull=False), then=Concat(
                    F('pricing_discount_percentage'),
                    Value('%'),
                    output_field=CharField()
                ))
            ),
            operated_as_status=Case(
                When(Q(applies_to_commercial=True) & Q(applies_to_private=True), then=2),
                When(applies_to_commercial=True, then=1),
                When(applies_to_private=True, then=3),
                default=0,
                output_field=IntegerField()
            )
        )


class FuelAgreementPricingManual(FuelAgreementPricing):
    agreement = models.ForeignKey("supplier.FuelAgreement", verbose_name=_("Agreement"),
                                  on_delete=models.CASCADE, related_name="pricing_manual")
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 limit_choices_to={'details__type_id': 8, 'airport_details__isnull': False},
                                 on_delete=models.CASCADE, related_name="agreement_pricing_for_location_manual")
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            on_delete=models.CASCADE, null=True,
                            related_name="agreement_pricing_for_ipa_manual")
    fuel = models.ForeignKey("core.FuelType", verbose_name=_("Fuel"),
                             on_delete=models.CASCADE, null=True,
                             related_name='agreement_pricing_for_fuel_manual')
    client = models.ForeignKey("organisation.Organisation", verbose_name=_("Client"),
                               on_delete=models.CASCADE, null=True, blank=True,
                               related_name="agreement_pricing_for_client_manual")
    price_active = models.BooleanField(_("Price Is Active?"), default=True)
    pricing_discount_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Discount Unit"),
                                              on_delete=models.RESTRICT, db_column="pricing_discount_unit",
                                              null=True, blank=True)
    pricing_discount_percentage = models.DecimalField(_("Pricing Discount Percentage"), max_digits=6, decimal_places=4,
                                                      null=True)
    pricing_discount_amount = models.DecimalField(_("Pricing Discount Amount"), max_digits=12, decimal_places=4,
                                                  null=True)
    flight_type = models.ForeignKey("core.FlightType", verbose_name=_("Flight Type"),
                                    on_delete=models.RESTRICT, db_column="flight_type")
    destination_type = models.ForeignKey("core.GeographichFlightType", verbose_name=_("Destination Type"),
                                         on_delete=models.RESTRICT, db_column="destination_type")
    band_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Band Unit"),
                                 on_delete=models.RESTRICT, db_column="band_uom",
                                 null=True, blank=True)
    band_start = models.DecimalField(_("Band Start"), max_digits=12, decimal_places=2,
                                     null=True, blank=True)
    band_end = models.DecimalField(_("Band End"), max_digits=12, decimal_places=2,
                                   null=True, blank=True)
    source_document_url = models.ForeignKey("organisation.OrganisationDocument", verbose_name=_("Source Document"),
                                            on_delete=models.SET_NULL, db_column="source_document_url",
                                            null=True)
    comment = models.CharField(_("Comment"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=True)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)
    parent_entry = models.ForeignKey("FuelAgreementPricingManual", on_delete=models.SET_NULL, null=True,
                                     related_name='child_entries')
    specific_handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Specific Handler"),
                                         on_delete=models.RESTRICT, null=True, blank=True,
                                         related_name="specific_discount_pricing",
                                         limit_choices_to={'handler_details__isnull': False})
    specific_apron = models.ForeignKey("core.ApronType", verbose_name=_("Specific Apron"),
                                       on_delete=models.RESTRICT, null=True, blank=True,
                                       related_name="specific_discount_pricing")
    specific_hookup_method = models.ForeignKey("core.HookupMethod", verbose_name=_("Specific Hookup Method"),
                                               null=True, blank=True, on_delete=models.RESTRICT)
    delivery_methods = models.ManyToManyField("core.FuelEquipmentType",
                                              verbose_name=_('Delivery Method(s)'),
                                              through='FuelAgreementPricingManualDeliveryMethods',
                                              related_name='fuel_agreement_pricing_discount', blank=True)

    objects = FuelAgreementPricingManualWithDetailsManager().from_queryset(FuelAgreementPricingQueryset)()

    # Non-DB fields
    market_pricing_base = None

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_manual'

    def __str__(self):
        return f'{self.pk}'

    @property
    def cascade_to_fees(self):
        _, cascade_to_fees = self.parent_inclusive_taxes

        return cascade_to_fees

    @property
    def inclusive_taxes(self):
        tax_cats = list(self.included_taxes.values_list('tax_category', flat=True))
        cascade_to_fees = any(self.included_taxes.values_list('applies_to_fees', flat=True))

        if None in tax_cats:
            return (['A'], cascade_to_fees)
        else:
            return (tax_cats, cascade_to_fees)

    @inclusive_taxes.setter
    def inclusive_taxes(self, value: tuple):
        inclusive_taxes, cascade_to_fees = value

        if 'A' in inclusive_taxes:
            inclusive_taxes = [None]

        FuelAgreementPricingManualIncludingTaxes.objects.filter(
            Q(pricing=self), ~Q(tax_category_id__in=inclusive_taxes)).delete()

        for cat in inclusive_taxes:
            FuelAgreementPricingManualIncludingTaxes.objects.update_or_create(
                pricing=self,
                tax_category_id=cat,
                defaults={'applies_to_fees': bool(cascade_to_fees)}
            )

    @property
    def inclusive_taxes_str(self):
        parent_entry = self.parent_entry or self
        included_cats = list(parent_entry.included_taxes.values_list('tax_category__name', flat=True))

        if None in included_cats:
            return 'All Applicable Taxes'
        else:
            return ', '.join(included_cats)

    @property
    def parent_inclusive_taxes(self):
        '''
        During creation/edition/superseding the inclusive taxes are recorded against the parent row.
        During calculation any row can apply, so if multiple bands exist, we need to check the parent
        entry for tax/fee inclusiveness.
        '''
        return (self.parent_entry.inclusive_taxes if self.parent_entry else self.inclusive_taxes)

    @property
    def is_percentage(self):
        return self.pricing_discount_unit is None

    @property
    def discount_applied_str(self):
        if self.is_percentage:
            return f'{self.pricing_discount_percentage}%'
        else:
            return f'{self.pricing_discount_amount} {self.pricing_discount_unit.description}'

    @property
    def pricing_link(self):
        return f'<a href="{self.url}">Agreement - Discount</a>'

    @property
    def specific_handler_link(self):
        if self.specific_handler:
            return f'<a href="{self.specific_handler.get_absolute_url()}">' \
                   f'{self.specific_handler.full_repr}</a>'

    @property
    def url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.agreement_id})

    def get_discount_datatable_str(self):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        if self.pricing_discount_amount is not None:
            formatted_discount = '{:.2f}'.format(self.pricing_discount_amount)

            if Decimal(formatted_discount) != self.pricing_discount_amount:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount} {self.pricing_discount_unit.description_short}',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.pricing_discount_amount, 2, 6, normalize_decimals=True)}'
                                 f' {self.pricing_discount_unit.description_short}',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f' {self.pricing_discount_unit.description_short}'
        else:
            formatted_discount = '{:.2f}'.format(self.pricing_discount_percentage)

            if Decimal(formatted_discount) != self.pricing_discount_percentage:
                formatted_discount = get_datatable_text_with_tooltip(
                    text=f'{formatted_discount}%',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.pricing_discount_percentage, 2, 6, normalize_decimals=True)}%',
                    tooltip_enable_html=True
                )
            else:
                formatted_discount += f'%'

        return formatted_discount


class FuelAgreementPricingFormulaDeliveryMethods(models.Model):
    pricing = models.ForeignKey('FuelAgreementPricingFormula', verbose_name=_("Formula Agreement Pricing"),
                                on_delete=models.RESTRICT)
    delivery_method = models.ForeignKey("core.FuelEquipmentType", verbose_name=_("Delivery Method"),
                                        on_delete=models.RESTRICT)

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_formulae_delivery_methods'


class FuelAgreementPricingFormulaWithDetailsManager(ArchivableModelManager):
    def with_details(self):
        return self.annotate(
            icao_iata=Case(
                When(Q(location__airport_details__iata_code__isnull=True)
                     | Q(location__airport_details__iata_code=''), then=F(
                    'location__airport_details__icao_code')),
                When(Q(location__airport_details__icao_code__isnull=True)
                     | Q(location__airport_details__icao_code=''), then=F(
                    'location__airport_details__iata_code')),
                default=Concat(
                    'location__airport_details__icao_code',
                    Value(' / '),
                    'location__airport_details__iata_code',
                    output_field=CharField()
                )
            ),
            ipa_name=Case(
                When(Q(ipa__details__registered_name__isnull=True)
                     | Q(ipa__details__registered_name=''), then=F(
                    'ipa__details__trading_name')),
                When(Q(ipa__details__trading_name__isnull=True)
                     | Q(ipa__details__trading_name=''), then=F(
                    'ipa__details__registered_name')),
                default=Concat(
                    'ipa__details__registered_name',
                    Value(' T/A '),
                    'ipa__details__trading_name',
                    output_field=CharField()
                )
            ),
            specific_client=Case(
                When(Q(client__details__registered_name__isnull=True)
                     | Q(client__details__registered_name=''), then=F(
                    'client__details__trading_name')),
                When(Q(client__details__trading_name__isnull=True)
                     | Q(client__details__trading_name=''), then=F(
                    'client__details__registered_name')),
                default=Concat(
                    'client__details__registered_name',
                    Value(' T/A '),
                    'client__details__trading_name',
                    output_field=CharField()
                )
            ),
            quantity_band=Case(
                When(Q(band_uom__isnull=False), then=Concat(
                    CommaSeparatedDecimalOrInteger(F('band_start')),
                    Value(' - '),
                    CommaSeparatedDecimalOrInteger(F('band_end')),
                    Value(' '),
                    F('band_uom__description_plural'),
                    output_field=CharField()
                ))
            ),
            index=Concat(
                F('pricing_index__fuel_index__provider__details__trading_name'),
                Value(' ('),
                F('pricing_index__fuel_index__provider__details__registered_name'),
                Value(') '),
                F('pricing_index__fuel_index__name'),
                Case(
                    When(Q(pricing_index__index_price_is_high=True), then=Value(' / High')),
                    When(Q(pricing_index__index_price_is_mean=True), then=Value(' / Mean')),
                    When(Q(pricing_index__index_price_is_low=True), then=Value(' / Low')),
                ),
                Case(
                    When(Q(pricing_index__index_period_is_daily=True), then=Value(' / Prior Day')),
                    When(Q(pricing_index__index_period_is_weekly=True), then=Value(' / Prior Week')),
                    When(Q(pricing_index__index_period_is_fortnightly=True), then=Value(' / Prior Fortnight')),
                    When(Q(pricing_index__index_period_is_monthly=True), then=Value(' / Prior Month')),
                ),
                Case(
                    When(Q(index_period_is_lagged=True), then=Value(' / Lagged')),
                ),
                Case(
                    When(Q(index_period_is_lagged=True, index_period_is_grace=True), then=Value(', Grace')),
                    When(Q(index_period_is_grace=True), then=Value(' / Grace')),
                ),
            ),
            differential_value_string=ExpressionWrapper(
                F('differential_value'),
                output_field=CharField()
            ),
            differential=Concat(
                CommaSeparatedDecimalRoundTo2(F('differential_value_string')),
                Value(' '),
                F('differential_pricing_unit__description_short'),
                output_field=CharField()
            ),
            operated_as_status=Case(
                When(Q(applies_to_commercial=True) & Q(applies_to_private=True), then=2),
                When(applies_to_commercial=True, then=1),
                When(applies_to_private=True, then=3),
                default=0,
                output_field=IntegerField()
            )
        )


class FuelAgreementPricingFormula(FuelAgreementPricing):
    INDEX_PRICING_STATUS_DETAILS = {
        0: {'code': 0, 'detail': 'OK', 'background_color': '#c3e6cb', 'text_color': '#000'},
        1: {'code': 1, 'detail': 'OK (Unpublished)', 'background_color': '#c3e6cb', 'text_color': '#000'},
        2: {'code': 2, 'detail': 'Pricing Expired', 'background_color': '#e55353', 'text_color': '#fff'},
        3: {'code': 3, 'detail': 'No Pricing', 'background_color': '#000', 'text_color': '#fff'},
    }

    agreement = models.ForeignKey("supplier.FuelAgreement", verbose_name=_("Agreement"),
                                  on_delete=models.CASCADE, related_name="pricing_formulae")
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 limit_choices_to={'details__type_id': 8, 'airport_details__isnull': False},
                                 on_delete=models.CASCADE, related_name="agreement_pricing_for_location_formulae")
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            on_delete=models.CASCADE, null=True,
                            related_name="agreement_pricing_for_ipa_formulae")
    fuel = models.ForeignKey("core.FuelType", verbose_name=_("Fuel"),
                             on_delete=models.CASCADE, null=True,
                             related_name='agreement_pricing_for_fuel_formulae')
    client = models.ForeignKey("organisation.Organisation", verbose_name=_("Client"),
                               on_delete=models.CASCADE, null=True, blank=True,
                               related_name="agreement_pricing_for_client_formulae")
    price_active = models.BooleanField(_("Price Is Active?"), default=True)
    pricing_index = models.ForeignKey("pricing.FuelIndexDetails", verbose_name=_("Pricing Index"),
                                      on_delete=models.RESTRICT)
    index_period_is_lagged = models.BooleanField(_("Period Is Lagged?"), default=False)
    index_period_is_grace = models.BooleanField(_("Period Is Grace?"), default=False)
    differential_value = models.DecimalField(_("Differential Value"), max_digits=12, decimal_places=6)
    differential_pricing_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Differential Pricing Unit"),
                                                  on_delete=models.RESTRICT, db_column="differential_pricing_unit")
    volume_conversion_method = models.ForeignKey("core.UnitOfMeasurementConversionMethod",
                                                 verbose_name=_("Volume Conversion Method"),
                                                 on_delete=models.RESTRICT, db_column="volume_conversion_method",
                                                 null=True, blank=True)
    volume_conversion_ratio_override = models.DecimalField(_("Volume Conversion Ratio Override"),
                                                           max_digits=12, decimal_places=4, null=True, blank=True)
    flight_type = models.ForeignKey("core.FlightType", verbose_name=_("Flight Type"),
                                    on_delete=models.RESTRICT, db_column="flight_type")
    destination_type = models.ForeignKey("core.GeographichFlightType", verbose_name=_("Destination Type"),
                                         on_delete=models.RESTRICT, db_column="destination_type")
    band_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Band Unit"),
                                 on_delete=models.RESTRICT, db_column="band_uom",
                                 null=True, blank=True)
    band_start = models.DecimalField(_("Band Start"), max_digits=12, decimal_places=2,
                                     null=True, blank=True)
    band_end = models.DecimalField(_("Band End"), max_digits=12, decimal_places=2,
                                   null=True, blank=True)
    source_document_url = models.ForeignKey("organisation.OrganisationDocument", verbose_name=_("Source Document"),
                                            on_delete=models.SET_NULL, db_column="source_document_url",
                                            null=True)
    comment = models.CharField(_("Comment"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=True)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)
    parent_entry = models.ForeignKey("FuelAgreementPricingFormula", on_delete=models.SET_NULL, null=True,
                                     related_name='child_entries')
    specific_handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Specific Handler"),
                                         on_delete=models.RESTRICT, null=True, blank=True,
                                         related_name="specific_formula_pricing",
                                         limit_choices_to={'handler_details__isnull': False})
    specific_apron = models.ForeignKey("core.ApronType", verbose_name=_("Specific Apron"),
                                       on_delete=models.RESTRICT, null=True, blank=True,
                                       related_name="specific_formula_pricing")
    specific_hookup_method = models.ForeignKey("core.HookupMethod", verbose_name=_("Specific Hookup Method"),
                                               null=True, blank=True, on_delete=models.RESTRICT)
    delivery_methods = models.ManyToManyField("core.FuelEquipmentType",
                                              verbose_name=_('Delivery Method(s)'),
                                              through='FuelAgreementPricingFormulaDeliveryMethods',
                                              related_name='fuel_agreement_pricing_formula', blank=True)

    objects = FuelAgreementPricingFormulaWithDetailsManager().from_queryset(FuelAgreementPricingFormulaQuerySet)()

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_formulae'

    def __str__(self):
        return f'{self.pk}'

    @property
    def cascade_to_fees(self):
        _, cascade_to_fees = self.parent_inclusive_taxes

        return cascade_to_fees

    @property
    def inclusive_taxes(self):
        tax_cats = list(self.included_taxes.values_list('tax_category', flat=True))
        cascade_to_fees = any(self.included_taxes.values_list('applies_to_fees', flat=True))

        if None in tax_cats:
            return (['A'], cascade_to_fees)
        else:
            return (tax_cats, cascade_to_fees)

    @inclusive_taxes.setter
    def inclusive_taxes(self, value: tuple):
        inclusive_taxes, cascade_to_fees = value

        if 'A' in inclusive_taxes:
            inclusive_taxes = [None]

        FuelAgreementPricingFormulaIncludingTaxes.objects.filter(
            Q(pricing=self), ~Q(tax_category_id__in=inclusive_taxes)).delete()

        for cat in inclusive_taxes:
            FuelAgreementPricingFormulaIncludingTaxes.objects.update_or_create(
                pricing=self,
                tax_category_id=cat,
                defaults={'applies_to_fees': bool(cascade_to_fees)}
            )

    @property
    def inclusive_taxes_str(self):
        parent_entry = self.parent_entry or self
        included_cats = list(parent_entry.included_taxes.values_list('tax_category__name', flat=True))

        if None in included_cats:
            return 'All Applicable Taxes'
        else:
            return ', '.join(included_cats)

    @property
    def parent_inclusive_taxes(self):
        '''
        During creation/edition/superseding the inclusive taxes are recorded against the parent row.
        During calculation any row can apply, so if multiple bands exist, we need to check the parent
        entry for tax/fee inclusiveness.
        '''
        return (self.parent_entry.inclusive_taxes if self.parent_entry else self.inclusive_taxes)

    @property
    def volume_conversion_units_str(self):
        if self.volume_conversion_ratio_override is None:
            return ''

        return f'{self.pricing_index.pricing_unit.uom.description}' \
               f' => {self.differential_pricing_unit.uom.description}'

    @property
    def pricing_index_status_badge(self):
        status_code = getattr(self, 'index_pricing_status', None)

        if status_code is None:
            return ''

        return get_datatable_badge(
            badge_text=self.INDEX_PRICING_STATUS_DETAILS[status_code]['detail'],
            badge_class='datatable-badge-normal',
            background_color=self.INDEX_PRICING_STATUS_DETAILS[status_code]['background_color'],
            text_color=self.INDEX_PRICING_STATUS_DETAILS[status_code]['text_color']
        )


    @property
    def pricing_link(self):
        return f'<a href="{self.url}">Agreement - Formula</a>'

    @property
    def specific_handler_link(self):
        if self.specific_handler:
            return f'<a href="{self.specific_handler.get_absolute_url()}">' \
                   f'{self.specific_handler.full_repr}</a>'

    @property
    def url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.agreement_id})

    def get_differential_datatable_str(self):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        formatted_differential = '{:.2f}'.format(self.differential_value)

        if Decimal(formatted_differential) != self.differential_value:
            formatted_differential = get_datatable_text_with_tooltip(
                text=f'{formatted_differential} {self.differential_pricing_unit.description_short}',
                span_class='pricing-tooltip',
                tooltip_text=f'{custom_round_to_str(self.differential_value, 2, 6, normalize_decimals=True)}'
                             f' {self.differential_pricing_unit.description_short}',
                tooltip_enable_html=True
            )
        else:
            formatted_differential += f' {self.differential_pricing_unit.description_short}'

        return formatted_differential

    def get_price_calculation_breakdown(self, index_price_obj, converted_index_price):
        index_dets = index_price_obj.fuel_index_details
        index_price_str = f"<b>{index_price_obj.price_repr}</b>"

        if self.differential_pricing_unit != index_price_obj.pricing_unit:
            index_price_str = f"<b>{converted_index_price} {self.differential_pricing_unit}</b> " \
                              f"({index_price_obj.price_repr})"

        return f"Fuel Index: <b>{index_dets.fuel_index} / {index_dets.structure_description}</b><br>" \
               f"Pricing Details: valid {index_price_obj.validity}, " \
               f"sourced by {index_price_obj.source_organisation.full_repr}<br>" \
               f"Index Pricing: <b>{index_price_str}</b><br>" \
               f"+ Differential: <b>{self.differential_value} {self.differential_pricing_unit}</b>"


class FuelAgreementPricingFormulaIncludingTaxes(models.Model):
    pricing = models.ForeignKey("FuelAgreementPricingFormula", verbose_name=_("Fuel Agreement Pricing Formula"),
                                on_delete=models.RESTRICT, related_name='included_taxes',
                                db_column='pricing_formulae_id')
    tax_category = models.ForeignKey("pricing.TaxCategory", verbose_name=_("Tax Category"),
                                     on_delete=models.RESTRICT, null=True, blank=True)
    applies_to_fees = models.BooleanField(default=False, verbose_name=_("Cascade to Fees?"))

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_formulae_inclusive_taxes'


class FuelAgreementPricingManualIncludingTaxes(models.Model):
    pricing = models.ForeignKey("FuelAgreementPricingManual", verbose_name=_("Fuel Agreement Pricing Manual"),
                                on_delete=models.RESTRICT, related_name='included_taxes',
                                db_column='pricing_manual_id')
    tax_category = models.ForeignKey("pricing.TaxCategory", verbose_name=_("Tax Category"),
                                     on_delete=models.RESTRICT, null=True, blank=True)
    applies_to_fees = models.BooleanField(default=False, verbose_name=_("Cascade to Fees?"))

    class Meta:
        db_table = 'suppliers_fuel_agreements_pricing_manual_inclusive_taxes'
