from datetime import datetime, time, timezone
from collections import defaultdict, namedtuple
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.postgres.aggregates import StringAgg
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import BooleanField, Case, Count, CharField, ExpressionWrapper, Exists, F, IntegerField, \
    OuterRef, Q, Value, When
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from core.templatetags.currency_uom_tags import custom_round_to_str
from core.utils.custom_query_expressions import CommaSeparatedDecimal
from core.utils.datatables_functions import get_datatable_text_with_tooltip
from pricing.mixins import PricingCalculationMixin
from pricing.utils import check_fuel_band, check_weight_band, get_uom_conversion_rate


class FuelFeeCategory(models.Model):
    name = models.CharField(_("Name"), max_length=200)
    applies_ooh = models.BooleanField(_("Applies OOH?"), default=False)
    applies_to_overwing_only = models.BooleanField(_("Applies To Over-Wing Only?"), default=False)
    applies_for_no_fuel_uplift = models.BooleanField(_("Applies For No Fuel Uplift?"), default=False)
    applies_for_defueling = models.BooleanField(_("Applies For Defueling?"), default=False)
    applies_for_multi_vehicle_uplift = models.BooleanField(_("Applies For Multi-Vehicle Uplift?"), default=False)

    class Meta:
        db_table = 'fees_fuel_categories'

    def __str__(self):
        return self.name


class SupplierFuelFeeQueryset(models.QuerySet):
    def with_location(self):
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
            ))

    def with_rate_details(self):
        return self.with_location().annotate(
            rate_count=Count('rates'),
            has_weight_band=Exists(self.filter(pk=OuterRef('pk'), rates__weight_band__isnull=False)),
            has_quantity_band=Exists(self.filter(pk=OuterRef('pk'), rates__quantity_band_uom__isnull=False)),
            specific_fuel=StringAgg(
                'rates__specific_fuel__name',
                delimiter=', ',
                distinct=True,
                default=Value('--')
            ),
            destination_type=StringAgg(
                'rates__destination_type__name',
                delimiter=', ',
                distinct=True,
                default=Value('--')
            ),
            flight_type=StringAgg(
                'rates__flight_type__name',
                delimiter=', ',
                distinct=True,
                default=Value('--')
            ),
            operated_as_status=Case(
                When(Exists(self.filter(pk=OuterRef('pk'), rates__applies_to_commercial=True)) &
                     Exists(self.filter(pk=OuterRef('pk'), rates__applies_to_private=True)), then=2),
                When(Exists(self.filter(pk=OuterRef('pk'), rates__applies_to_commercial=True)), then=1),
                When(Exists(self.filter(pk=OuterRef('pk'), rates__applies_to_private=True)), then=3),
                default=0,
                output_field=IntegerField()
            ),
        )


class SupplierFuelFee(models.Model):
    local_name = models.CharField(_("Local Name"), max_length=100, null=True, blank=True)
    supplier = models.ForeignKey("organisation.Organisation", verbose_name=_("Supplier"),
                                 on_delete=models.CASCADE, related_name="fuel_fees_where_is_supplier")
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 on_delete=models.CASCADE, related_name="fuel_fees_where_is_location")
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            on_delete=models.CASCADE, related_name="fuel_fees_where_is_ipa",
                            null=True)
    fuel_fee_category = models.ForeignKey("FuelFeeCategory", verbose_name=_("Fuel Fee Category"),
                                          db_column="fuel_fee_category", on_delete=models.RESTRICT,
                                          related_name="fees_in_category")
    pricing_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Unit"),
                                     on_delete=models.RESTRICT, related_name="fees_using_unit")
    related_pld = models.ForeignKey("pricing.FuelPricingMarketPld", null=True, blank=True, on_delete=models.SET_NULL)

    objects = SupplierFuelFeeQueryset.as_manager()

    class Meta:
        db_table = 'suppliers_fuel_fees'

    def __str__(self):
        return self.local_name

    @property
    def applies_to_commercial(self):
        return self.rates.filter(applies_to_commercial=True).count()

    @property
    def applies_to_private(self):
        return self.rates.filter(applies_to_private=True).count()

    @property
    def display_name(self):
        return self.local_name or self.fuel_fee_category.name

    @property
    def unit_rate_string(self):
        if len(self.rates.all()) > 1:
            return 'Multiple Rates Apply'

        rate = self.rates.first()

        if rate.weight_band and rate.quantity_band_uom:
            return 'Bands Apply'
        elif rate.weight_band:
            return 'Weight Band Applies'
        elif rate.quantity_band_uom:
            return 'Quantity Band Applies'
        else:
            return self.rates.with_details().first().unit_rate_string_inc_conversion_short


class FuelFeeRateManager(models.Manager):
    def with_details(self):
        return self.annotate(
            native_price_string=ExpressionWrapper(
                CommaSeparatedDecimal(F('pricing_native_amount')),
                output_field=CharField()
            ),
            converted_price_string=ExpressionWrapper(
                CommaSeparatedDecimal(F('pricing_converted_amount')),
                output_field=CharField()
            ),
        )

    def with_location(self):
        return self.annotate(
            icao_iata=Case(
                When(Q(supplier_fuel_fee__location__airport_details__iata_code__isnull=True)
                     | Q(supplier_fuel_fee__location__airport_details__iata_code=''), then=F(
                    'supplier_fuel_fee__location__airport_details__icao_code')),
                When(Q(supplier_fuel_fee__location__airport_details__icao_code__isnull=True)
                     | Q(supplier_fuel_fee__location__airport_details__icao_code=''), then=F(
                    'supplier_fuel_fee__location__airport_details__iata_code')),
                default=Concat(
                    'supplier_fuel_fee__location__airport_details__icao_code',
                    Value(' / '),
                    'supplier_fuel_fee__location__airport_details__iata_code',
                    output_field=CharField()
                )
            ))


class FuelFeeRateQueryset(models.QuerySet):
    def active(self):
        return self.filter(Q(price_active=True))

    def applies_at_dow_and_time(self, datetime_utc: datetime, datetime_lt: datetime):
        dow_utc = datetime_utc.weekday() + 1
        dow_lt = datetime_lt.weekday() + 1
        time_utc = datetime_utc.time()
        time_lt = datetime_lt.time()

        return self.filter(Q(validity_periods__isnull=True)
                           | (Q(validity_periods__is_local=True)
                              & Q(validity_periods__valid_from_dow__lte=dow_lt)
                              & Q(validity_periods__valid_to_dow__gte=dow_lt)
                              & Q(validity_periods__valid_from_time__lte=time_lt)
                              & Q(validity_periods__valid_to_time__gte=time_lt))
                           | (Q(validity_periods__is_local=False)
                              & Q(validity_periods__valid_from_dow__lte=dow_utc)
                              & Q(validity_periods__valid_to_dow__gte=dow_utc)
                              & Q(validity_periods__valid_from_time__lte=time_utc)
                              & Q(validity_periods__valid_to_time__gte=time_utc)))

    def applies_at_location(self, airport):
        return self.filter(Q(supplier_fuel_fee__location=airport))

    def applies_for_fuel_taken(self, is_fuel_taken, is_defueling):
        if is_fuel_taken:
            return self.filter(supplier_fuel_fee__fuel_fee_category__applies_for_no_fuel_uplift=False,
                               supplier_fuel_fee__fuel_fee_category__applies_for_defueling=False)
        elif is_defueling:
            return self.filter(supplier_fuel_fee__fuel_fee_category__applies_for_defueling=True)
        else:
            return self.filter(supplier_fuel_fee__fuel_fee_category__applies_for_no_fuel_uplift=True)

    def applies_for_multi_vehicle_uplift(self, is_multi_vehicle):
        if not is_multi_vehicle:
            return self.filter(supplier_fuel_fee__fuel_fee_category__applies_for_multi_vehicle_uplift=False)
        else:
            return self

    def applies_to_apron(self, apron):
        if apron is not None:
            return self.filter(Q(specific_apron__isnull=True) | Q(specific_apron=apron))
        else:
            return self

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

    def applies_to_delivery_method(self, delivery_methods):
        if delivery_methods:
            return self.filter(
                Q(delivery_method__isnull=True) | Q(delivery_method__in=delivery_methods))
        else:
            return self

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
            Q(specific_fuel__isnull=True) | Q(specific_fuel__category=fuel_cat)
        )

    def applies_to_fuel_type(self, fuel_type):
        if fuel_type is not None:
            return self.filter(
                Q(specific_fuel__isnull=True) | Q(specific_fuel=fuel_type)
            )
        else:
            return self

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
            return self.filter(Q(specific_handler__isnull=True)
                               | (Q(specific_handler_is_excluded=False) & Q(specific_handler=handler))
                               | (Q(specific_handler_is_excluded=True) & ~Q(specific_handler=handler)))
        else:
            return self

    def filter_by_source_doc(self, used_plds, used_agreement_ids):
        return self.filter(
            (Q(source_agreement__isnull=True) | Q(source_agreement__pk__in=used_agreement_ids)) &
            (Q(supplier_fuel_fee__related_pld__isnull=True) |
             Q(supplier_fuel_fee__related_pld__pk__in=used_plds))
        )

    def filter_by_date_for_calc(self, validity_date_utc):
        """
        This filter needs to include valid and expired fees (to use in case no valid pricing is present).
        We are always excluding future fees.
        """
        return self.annotate(
            expiry_date=F("valid_to_date"),
            is_expired=Case(
                When(Q(valid_to_date__lt=validity_date_utc),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(Q(valid_from_date__lte=validity_date_utc))

    def for_destination(self, destination_type):
        qs = self

        if destination_type != 'ALL':
            qs = qs.filter(Q(destination_type='ALL') | Q(destination_type=destination_type))

        return qs

    def with_details(self):
        return self.annotate(
            native_price_string=ExpressionWrapper(
                CommaSeparatedDecimal(F('pricing_native_amount')),
                output_field=CharField()
            ),
            converted_price_string=ExpressionWrapper(
                CommaSeparatedDecimal(F('pricing_converted_amount')),
                output_field=CharField()
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
        Annotate specificity score for each applicable rate, that will be used to determine the rate used
        after all filters are applied (rate with the highest score, which generally means more specific, wins).
        This is based on the similar solution used in the APC for taxes.
        - Level 1: valid: 1000000, expired: 0
        - Level 2: handler-specific: 100000, generic: 0
        - Level 3: apron-specific: 10000, generic: 0
        - Level 4: with specific delivery method: 1000, else: 0
        - Level 5: with specific flight type: 100, else: 0
        - Level 6: with specific destination: 10, else: 0
        """
        return self.annotate(
            specificity_score=Case(
                When(is_expired=False, then=1000000), default=0
            ) + Case(
                When(Q(specific_handler__isnull=False), then=100000), default=0
            ) + Case(
                When(Q(specific_apron__isnull=False), then=10000), default=0
            ) + Case(
                When(Q(delivery_method__isnull=False), then=1000), default=0
            ) + Case(
                When(~Q(flight_type='A'), then=100), default=0
            ) + Case(
                When(~Q(destination_type='ALL'), then=10), default=0
            )
        )


# Note: parent/child relation is not used here, because we have SupplierFuelFee on top of rates and we only ever associate
# one set of Rate for the same Fee
# Blank is not used for delivery_method and specific_fuel, because we want the select2 field to display the first value,
# 'All' when the value is Null
class SupplierFuelFeeRate(models.Model, PricingCalculationMixin):
    supplier_fuel_fee = models.ForeignKey("SupplierFuelFee", verbose_name=_("Supplier Fuel Fee"),
                                          on_delete=models.CASCADE, related_name="rates")
    delivery_method = models.ForeignKey("core.FuelEquipmentType", verbose_name=_("Delivery Method"),
                                        on_delete=models.SET_NULL, null=True)
    specific_fuel = models.ForeignKey("core.FuelType", verbose_name=_("Specific Fuel"),
                                      on_delete=models.CASCADE, null=True)
    flight_type = models.ForeignKey("core.FlightType", verbose_name=_("Flight Type"),
                                    on_delete=models.RESTRICT, db_column="flight_type")
    destination_type = models.ForeignKey("core.GeographichFlightType", verbose_name=_("Destination Type"),
                                         on_delete=models.RESTRICT, db_column="destination_type")
    quantity_band_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Quantity Band Unit"),
                                          on_delete=models.RESTRICT, db_column="quantity_band_uom",
                                          null=True, blank=True)
    quantity_band_start = models.DecimalField(_("Quantity Band Start"), max_digits=12, decimal_places=2,
                                              null=True)
    quantity_band_end = models.DecimalField(_("Quantity Band End"), max_digits=12, decimal_places=2,
                                            null=True)
    weight_band = models.ForeignKey("aircraft.AircraftWeightUnit", verbose_name=_("Weight Band Unit"),
                                    on_delete=models.RESTRICT, null=True, blank=True)
    weight_band_start = models.DecimalField(_("Weight Band Start"), max_digits=12, decimal_places=2,
                                            null=True)
    weight_band_end = models.DecimalField(_("Weight Band End"), max_digits=12, decimal_places=2,
                                          null=True)
    source_document_url = models.ForeignKey("organisation.OrganisationDocument", verbose_name=_("Source Document"),
                                            on_delete=models.SET_NULL, db_column="source_document_url",
                                            null=True)
    price_active = models.BooleanField(_("Price Active"), default=True)
    pricing_native_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Native Unit"),
                                            related_name='supplier_fuel_fee_rate_pricing_native',
                                            on_delete=models.CASCADE)
    pricing_native_amount = models.DecimalField(_("Pricing Native Amount"), max_digits=12, decimal_places=6)
    supplier_exchange_rate = models.DecimalField(_("Supplier Exchange Rate"),
                                                 max_digits=15, decimal_places=6,
                                                 null=True, blank=True)
    pricing_converted_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Converted Unit"),
                                               related_name='supplier_fuel_fee_rate_pricing_converted',
                                               null=True, blank=True,
                                               on_delete=models.CASCADE)
    pricing_converted_amount = models.DecimalField(_("Pricing Converted Amount"),
                                                   max_digits=12, decimal_places=6,
                                                   null=True, blank=True)
    comment = models.CharField(_("Comment"), max_length=500, null=True, blank=True)
    valid_from_date = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to_date = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False, null=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    source_agreement = models.ForeignKey("supplier.FuelAgreement", verbose_name=_("Source Agreement"),
                                         related_name='associated_fees',
                                         on_delete=models.RESTRICT, null=True)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=True)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True)
    specific_handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Specific Handler"),
                                         on_delete=models.RESTRICT, null=True, blank=True,
                                         related_name="specific_fuel_fees",
                                         limit_choices_to={'handler_details__isnull': False})
    specific_handler_is_excluded = models.BooleanField(_("Spec. Handler Is Excluded?"), default=False)
    specific_apron = models.ForeignKey("core.ApronType", verbose_name=_("Specific Apron"),
                                       on_delete=models.RESTRICT, null=True, blank=True,
                                       related_name="specific_fuel_fees")
    specific_hookup_method = models.ForeignKey("core.HookupMethod", verbose_name=_("Specific Hookup Method"),
                                               null=True, blank=True, on_delete=models.RESTRICT)

    objects = FuelFeeRateManager.from_queryset(FuelFeeRateQueryset)()

    class Meta:
        db_table = 'suppliers_fuel_fees_rates'

    def __str__(self):
        return f'{self.pk}'

    @property
    def operated_as(self):
        if self.applies_to_commercial and self.applies_to_private:
            return 'Commercial, Private'
        elif self.applies_to_commercial:
            return 'Commercial'
        elif self.applies_to_private:
            return 'Private'

    @property
    def pricing_unit(self):
        if self.pricing_converted_unit is not None:
            return self.pricing_converted_unit
        else:
            return self.pricing_native_unit

    def get_unit_price(self):
        if self.pricing_converted_unit is not None:
            return self.pricing_converted_amount
        else:
            return self.pricing_native_amount

    @property
    def quantity_band(self):
        if self.quantity_band_uom is not None:
            return f'{self.quantity_band_start} - {self.quantity_band_end} {self.quantity_band_uom.description_plural}'

    @property
    def weight_band_string(self):
        if self.weight_band is not None:
            return f'{self.weight_band_start} - {self.weight_band_end} {self.weight_band.name}'

    @property
    def unit_rate_string(self):
        if self.pricing_converted_amount is not None:
            return f'{self.converted_price_string} {self.pricing_converted_unit.description}'
        else:
            return f'{self.native_price_string} {self.pricing_native_unit.description}'

    @property
    def unit_rate_string_inc_conversion_long(self):
        if self.pricing_converted_amount is not None:
            return f'{self.native_price_string} {self.pricing_native_unit.description}' \
                   f' => {self.converted_price_string} {self.pricing_converted_unit.description}'
        else:
            return f'{self.native_price_string} {self.pricing_native_unit.description}'

    @property
    def unit_rate_string_inc_conversion_short(self):
        if self.pricing_converted_amount is not None:
            return f'{self.native_price_string} {self.pricing_native_unit.description_short}' \
                   f' => {self.converted_price_string} {self.pricing_converted_unit.description_short}'
        else:
            return f'{self.native_price_string} {self.pricing_native_unit.description_short}'

    @property
    def currency(self):
        return self.pricing_unit.currency

    @property
    def uom(self):
        return self.pricing_unit.uom

    @property
    def is_historical(self):
        if self.source_agreement is not None:
            return self.valid_to_date and self.valid_to_date < datetime.now(timezone.utc).date() \
                or self.source_agreement.end_date and self.source_agreement.end_date < datetime.now(timezone.utc)
        else:
            return self.price_active

    @property
    def is_published(self):
        if self.source_agreement is not None:
            return self.source_agreement.is_published

        return True

    @property
    def specific_handler_link(self):
        if self.specific_handler:
            handler_link = f'<a href="{self.specific_handler.get_absolute_url()}">' \
                           f'{self.specific_handler.full_repr}</a>'

            if self.specific_handler_is_excluded:
                handler_link = f'Any, except {handler_link}'

            return handler_link

    @staticmethod
    def dow_period_string(dow_period):
        c = SupplierFuelFeeRateValidityPeriod

        return f'{c.DOW_SHORT_NAMES[dow_period.start]}' if dow_period.start == dow_period.end \
            else f'{c.DOW_SHORT_NAMES[dow_period.start]} - {c.DOW_SHORT_NAMES[dow_period.end]}'

    @property
    def validity_periods_per_day(self):
        """
        Group validity time periods for each Day of Week.
        """
        TimePeriod = namedtuple('TimePeriod', 'start end is_local')
        periods = self.validity_periods.order_by('valid_from_dow', 'valid_from_time').all()
        daily_periods = defaultdict(list)

        for p in periods:
            for day in range(p.valid_from_dow, p.valid_to_dow + 1):
                daily_periods[day].append(TimePeriod(p.valid_from_time, p.valid_to_time, p.is_local))

        return dict(sorted(daily_periods.items()))

    @property
    def validity_periods_grouped(self):
        """
        Group validity periods by merging periods covering the same days for more readable displaying.
        """
        DowPeriod = namedtuple('DowPeriod', 'start end')
        grouped_periods = defaultdict(list)
        period_days = []
        dow_period_time_periods = set()

        for k, v in self.validity_periods_per_day.items():
            is_consecutive_day = period_days[-1] == k - 1 if period_days else True
            all_periods_match = sorted(v) == sorted(dow_period_time_periods)

            if period_days and (not is_consecutive_day or not all_periods_match):
                grouped_periods[DowPeriod(period_days[0], period_days[-1])] = sorted(dow_period_time_periods,
                                                                                     key=lambda x: x.start)
                period_days = [k]
                dow_period_time_periods = set(v)
            else:
                period_days.append(k)
                dow_period_time_periods.update(v)

        if period_days:
            grouped_periods[DowPeriod(period_days[0], period_days[-1])] = sorted(dow_period_time_periods,
                                                                                 key=lambda x: x.start)

        return grouped_periods

    @property
    def validity_periods_sorted(self):
        return self.validity_periods.order_by('valid_from_dow', 'valid_from_time')

    @property
    def validity_periods_display(self):
        display_entries = {}

        for days, times in self.validity_periods_grouped.items():
            display_entries[self.dow_period_string(days)] = ", ".join(
                [p[0].strftime("%H:%M") + " - " + p[1].strftime("%H:%M") for p in times])

        return display_entries

    def apply_basic_notes(self):
        notes = [
            f"Category: <b>{self.supplier_fuel_fee.fuel_fee_category.name}</b>"
        ]

        if self.validity_periods.exists():
            is_local = self.validity_periods.first().is_local
            notes.append(
                f'This fee applies within the following periods ({"local times" if is_local else "UTC"}):<ul>'
                + "".join([f'<li>{self.dow_period_string(days)}: '
                           f'{", ".join([p[0].strftime("%H:%M") + " - " + p[1].strftime("%H:%M") for p in times])}</li>'
                           for days, times in self.validity_periods_grouped.items()]) + "</ul>"
            )

        return notes

    def convert_pricing_amount(self):
        """
        Convert the native amount using the supplier exchange rate, accounting for the unit.
        (The provided supplier XR is a currency XR, while the component stemming from
        the difference in uom between native and converted pricing units needs to be applied here)
        """
        if any([not self.pricing_native_unit, not self.pricing_converted_unit, not self.pricing_native_amount]):
            return

        uom_from = self.pricing_native_unit.uom
        uom_to = self.pricing_converted_unit.uom
        uom_conversion_rate = get_uom_conversion_rate(uom_from, uom_to, self.specific_fuel)

        # Account for currency divisions on either end
        curr_from = self.pricing_native_unit.currency
        curr_to = self.pricing_converted_unit.currency
        curr_from_div = curr_from.division_factor if self.pricing_native_unit.currency_division_used else 1
        curr_to_div = curr_to.division_factor if self.pricing_converted_unit.currency_division_used else 1
        curr_div_factor = Decimal(curr_from_div / curr_to_div)

        self.pricing_converted_amount = (Decimal(self.pricing_native_amount)
                                         * (Decimal(self.supplier_exchange_rate)
                                            * uom_conversion_rate / curr_div_factor)
                                         .quantize(Decimal('0.000001'), ROUND_HALF_UP))

    def get_pricing_datatable_str(self, for_sublist=False):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        formatted_native_pricing = '{:.2f}'.format(self.pricing_native_amount)

        if Decimal(formatted_native_pricing) != self.pricing_native_amount:
            formatted_native_pricing = get_datatable_text_with_tooltip(
                text=f'{formatted_native_pricing} {self.pricing_native_unit.description}',
                span_class='pricing-tooltip',
                tooltip_text=f'{custom_round_to_str(self.pricing_native_amount, 2, 6, normalize_decimals=True)}'
                             f' {self.pricing_native_unit.description}',
                tooltip_enable_html=True
            )
        else:
            formatted_native_pricing += f' {self.pricing_native_unit.description}'

        if self.pricing_converted_amount:
            formatted_converted_pricing = '{:.2f}'.format(self.pricing_converted_amount)

            if Decimal(formatted_converted_pricing) != self.pricing_converted_amount:
                formatted_converted_pricing = get_datatable_text_with_tooltip(
                    text=formatted_converted_pricing + f' {self.pricing_converted_unit.description}',
                    span_class='pricing-tooltip',
                    tooltip_text=f'{custom_round_to_str(self.pricing_converted_amount, 2, 6, normalize_decimals=True)}'
                                 f' {self.pricing_converted_unit.description}',
                    tooltip_enable_html=True
                )
            else:
                formatted_converted_pricing += f' {self.pricing_converted_unit.description}'

            if for_sublist:
                return f'{formatted_native_pricing} => {formatted_converted_pricing}'
            else:
                return f'{formatted_converted_pricing}<br>(Converted)'
        else:
            return f'{formatted_native_pricing}'

    def check_bands(self, uplift_qty, uplift_uom, fuel_type, aircraft_type):
        '''
        Due to uplift quantity being specified to 4 decimal places, we need to ensure
        that there are no gaps when checking bands, which currently have int values,
        so we extend the band end to the next band start minus 0.0001 (if next band exists).
        Weight band can be left alone for now, as weights are currently integers.
        '''
        next_quant_band_start = None

        if self.supplier_fuel_fee and self.quantity_band_end:
            next_quant_band_start = self.supplier_fuel_fee.rates \
                .filter(quantity_band_start__gt=self.quantity_band_end) \
                .order_by('quantity_band_start').values_list('quantity_band_start', flat=True).first()

        # Only extend if there is no gap larger than 1 between bands
        # (we have validation to prevent this now, but we can check it
        # just in case gaps are permissible in the future.)
        if next_quant_band_start and next_quant_band_start - self.quantity_band_end <= 1:
            self.quantity_band_end = Decimal(next_quant_band_start - Decimal(0.0001)).quantize(Decimal('0.0001'))

        bands_apply = check_fuel_band(self.quantity_band_uom, self.quantity_band_start,
                                      self.quantity_band_end, uplift_qty, uplift_uom, fuel_type) \
                      and check_weight_band(aircraft_type, self.weight_band, self.weight_band_start,
                                            self.weight_band_end)

        return bands_apply

    def update_validity_periods(self, val):
        new_period_pks = []

        for period in val:
            from_dow, to_dow, from_time, to_time, is_local = period

            # Create new entries for any period that has changed / does not exist
            period_obj, _ = SupplierFuelFeeRateValidityPeriod.objects.update_or_create(
                fuel_fee_rate=self, valid_from_dow=from_dow, valid_to_dow=to_dow,
                valid_from_time=from_time, valid_to_time=to_time, is_local=is_local
            )
            new_period_pks.append(period_obj.pk)

        # Remove any periods that are not untouched / newly created
        self.validity_periods.exclude(pk__in=new_period_pks).delete()


class SupplierFuelFeeRateValidityPeriod(models.Model):
    DOW_CHOICES = [
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday"),
    ]
    DOW_SHORT_NAMES = {
        1: "Mon",
        2: "Tue",
        3: "Wed",
        4: "Thu",
        5: "Fri",
        6: "Sat",
        7: "Sun",
    }

    fuel_fee_rate = models.ForeignKey("pricing.SupplierFuelFeeRate", verbose_name=_("Fuel Fee Validity Period"),
                                      on_delete=models.CASCADE, related_name='validity_periods')
    valid_from_dow = models.PositiveSmallIntegerField(_('Valid From DOW'), choices=DOW_CHOICES,
                                                      validators=[MinValueValidator(1), MaxValueValidator(7)])
    valid_to_dow = models.PositiveSmallIntegerField(_('Valid To DOW'), choices=DOW_CHOICES,
                                                    validators=[MinValueValidator(1), MaxValueValidator(7)])
    valid_from_time = models.TimeField(_('Valid From Time'), auto_now=False, auto_now_add=False)
    valid_to_time = models.TimeField(_('Valid To Time'), auto_now=False, auto_now_add=False)
    is_local = models.BooleanField(_('Local Time?'), default=False)

    class Meta:
        db_table = 'suppliers_fuel_fees_rates_validity_periods'

    def __str__(self):
        dow_str = f'{self.DOW_SHORT_NAMES[self.valid_from_dow]}-{self.DOW_SHORT_NAMES[self.valid_to_dow]}' \
            if self.valid_from_dow != self.valid_to_dow else f'{self.DOW_SHORT_NAMES[self.valid_from_dow]}'

        return f'{dow_str}, {self.valid_from_time}-{self.valid_to_time} ({"Local" if self.is_local else "UTC"})'

    @property
    def valid_all_day(self):
        if self.valid_from_time == time(0, 0, 0) and self.valid_to_time == time(23, 59, 59):
            return True

        return False

class SupplierAdditivePricing(models.Model):
    supplier = models.ForeignKey("organisation.Organisation", verbose_name=_("Supplier"),
                                 on_delete=models.CASCADE, related_name="supplied_additive_prices")
    additive = models.ForeignKey("core.FuelAdditive", verbose_name=_("Additive"),
                                 on_delete=models.CASCADE, related_name="prices")
    active = models.BooleanField(_("Is Active?"), default=True)
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=4,
                                     null=True)
    pricing_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Unit"),
                                     on_delete=models.RESTRICT, db_column="pricing_unit",
                                     null=True)
    price_on_request = models.BooleanField(_("Price on Request?"), default=False)
    moq_amount = models.DecimalField(_("MOQ Amount"), max_digits=4, decimal_places=2,
                                     null=True)
    moq_uom = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("MOQ Unit"),
                                on_delete=models.RESTRICT, db_column="moq_uom",
                                null=True)
    manufactured_on_demand = models.BooleanField(_("Manufactured on Demand?"), default=False)
    valid_from = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False, null=True, blank=True)
    valid_ufn = models.BooleanField(_("Valid UFN?"), default=False)
    physical_location = models.ForeignKey("core.Country", verbose_name=_("Physical Location"),
                                          on_delete=models.RESTRICT, db_column="physical_location",
                                          null=True)
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)

    class Meta:
        db_table = 'suppliers_additives_pricing'

    def __str__(self):
        return f'{self.pk}'
