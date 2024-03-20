from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import BooleanField, Case, CharField, DateField, ExpressionWrapper, F, Q, Value, When, \
    Exists, Min, Subquery, OuterRef, Func
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from app.storage_backends import FuelPricingMarketPldDocumentFilesStorage
from core.templatetags.currency_uom_tags import custom_round_to_str
from core.utils.datatables_functions import get_datatable_badge, get_datatable_text_with_tooltip
from organisation.models import OrganisationContactDetails, OrganisationPeople
from pricing.mixins import PricingCalculationMixin
from pricing.models import PricingBacklogEntry, PrioritizedModel, TaxRule
from pricing.utils import check_fuel_band, get_uom_conversion_rate


class FuelPricingMarketQueryset(models.QuerySet):
    def active(self):
        return self.filter(Q(price_active=True))

    def applies_at_location(self, airport):
        return self.filter(Q(supplier_pld_location__location=airport))

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

    def applies_to_fuel_cat(self, fuel_cat):
        return self.filter(
            Q(fuel__isnull=True) | Q(fuel__category=fuel_cat)
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

    def applies_to_flight_type(self, applicable_flight_types):
        return self.filter(
            Q(flight_type__in=applicable_flight_types)
        )

    def applies_to_fuel_type(self, fuel_type):
        return self.filter(
            Q(fuel__isnull=True) | Q(fuel=fuel_type)
        )

    def applies_to_handler(self, handler):
        if handler is not None:
            return self.filter(Q(specific_handler__isnull=True) | Q(specific_handler=handler))
        else:
            return self

    def filter_by_date_for_calc(self, validity_datetime_utc, extend_expired_client_spec_pricing):
        """
        This filter needs to include valid and expired pricing (to use in case no valid pricing is present).
        We are always excluding future pricing. Only include expired client-specific pricing if the relevant
        option is on.
        """
        validity_date_utc = validity_datetime_utc.date()

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
                    F("valid_to_date"),
                    Value('yyyy-MM-dd'),
                    function='to_char',
                    output_field=CharField()
                ),
                output_field=CharField()
            ),
            is_expired=Case(
                When(Q(valid_to_date__lt=validity_date_utc) |
                     Q(deleted_at__lt=validity_datetime_utc),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).filter(Q(valid_from_date__lte=validity_date_utc))

        if not extend_expired_client_spec_pricing:
            qs = qs.exclude(Q(client__isnull=False) & Q(is_expired=True))

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


class FuelPricingMarketManager(models.Manager):
    def with_details(self):
        return self.annotate(
            icao_iata=Case(
                When(Q(supplier_pld_location__location__airport_details__iata_code__isnull=True)
                     | Q(supplier_pld_location__location__airport_details__iata_code=''), then=F(
                    'supplier_pld_location__location__airport_details__icao_code')),
                When(Q(supplier_pld_location__location__airport_details__icao_code__isnull=True)
                     | Q(supplier_pld_location__location__airport_details__icao_code=''), then=F(
                    'supplier_pld_location__location__airport_details__iata_code')),
                default=Concat(
                    'supplier_pld_location__location__airport_details__icao_code',
                    Value(' / '),
                    'supplier_pld_location__location__airport_details__iata_code',
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
        )


class FuelPricingMarketDeliveryMethod(models.Model):
    pricing = models.ForeignKey('FuelPricingMarket', verbose_name=_("Market Pricing"),
                                on_delete=models.RESTRICT)
    delivery_method = models.ForeignKey("core.FuelEquipmentType", verbose_name=_("Delivery Method"),
                                        on_delete=models.RESTRICT)

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_delivery_methods'


class FuelPricingMarket(models.Model, PricingCalculationMixin):
    supplier_pld_location = models.ForeignKey("FuelPricingMarketPldLocation", verbose_name=_("PLD Location"),
                                              on_delete=models.CASCADE, related_name="fuel_pricing_market")
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            related_name="fuel_pricing_markets_where_is_ipa",
                            on_delete=models.RESTRICT, null=True)
    fuel = models.ForeignKey("core.FuelType", verbose_name=_("Fuel"),
                             on_delete=models.CASCADE, related_name='market_pricing_for_fuel')
    client = models.ForeignKey("organisation.Organisation", verbose_name=_("Client"),
                               on_delete=models.RESTRICT, null=True, blank=True,
                               related_name="fuel_pricing_markets_where_is_client")
    price_active = models.BooleanField(_("Price Is Active?"), default=True)
    pricing_native_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Native Unit"),
                                            related_name='fuel_pricing_market_where_native',
                                            on_delete=models.RESTRICT)
    pricing_native_amount = models.DecimalField(_("Pricing Native Amount"), max_digits=12, decimal_places=6)
    supplier_exchange_rate = models.DecimalField(_("Supplier Exchange Rate"),
                                                 max_digits=15, decimal_places=6,
                                                 null=True, blank=True)
    pricing_converted_unit = models.ForeignKey("core.PricingUnit", verbose_name=_("Pricing Converted Unit"),
                                               null=True, blank=True,
                                               related_name='fuel_pricing_market_where_converted',
                                               on_delete=models.RESTRICT)
    pricing_converted_amount = models.DecimalField(_("Pricing Converted Amount"),
                                                   max_digits=12, decimal_places=6,
                                                   null=True, blank=True)
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
    valid_from_date = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to_date = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False)
    is_latest = models.BooleanField(_("Is Latest?"), default=True)
    is_reviewed = models.BooleanField(_("Is Reviewed?"), default=False)
    is_published = models.BooleanField(_("Is Published?"), default=False)
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    review = models.ForeignKey("FuelPricingMarketReview", verbose_name=_("Review"),
                               on_delete=models.RESTRICT, null=True)
    applies_to_commercial = models.BooleanField(_("Applies To Commercial"), default=True)
    applies_to_private = models.BooleanField(_("Applies To Private"), default=True)
    parent_entry = models.ForeignKey("FuelPricingMarket", on_delete=models.SET_NULL, null=True,
                                     related_name='child_entries')
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True)
    is_pap = models.BooleanField(_("Posted Airport Pricing?"), default=False)
    specific_handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Specific Handler"),
                                         on_delete=models.RESTRICT, null=True, blank=True,
                                         related_name="specific_market_pricing",
                                         limit_choices_to={'handler_details__isnull': False})
    specific_apron = models.ForeignKey("core.ApronType", verbose_name=_("Specific Apron"),
                                       on_delete=models.RESTRICT, null=True, blank=True,
                                       related_name="specific_market_pricing")
    specific_hookup_method = models.ForeignKey("core.HookupMethod", verbose_name=_("Specific Hookup Method"),
                                               null=True, blank=True, on_delete=models.RESTRICT)
    delivery_methods = models.ManyToManyField("core.FuelEquipmentType",
                                              verbose_name=_('Delivery Method(s)'),
                                              through='FuelPricingMarketDeliveryMethod',
                                              related_name='fuel_market_pricing', blank=True)

    objects = FuelPricingMarketManager.from_queryset(FuelPricingMarketQueryset)()

    class Meta:
        db_table = 'suppliers_fuel_pricing_market'

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

        FuelPricingMarketIncludingTaxes.objects.filter(
            Q(pricing=self), ~Q(tax_category_id__in=inclusive_taxes)).delete()

        for cat in inclusive_taxes:
            FuelPricingMarketIncludingTaxes.objects.update_or_create(
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
    def pricing_unit(self):
        if self.pricing_converted_unit is not None:
            return self.pricing_converted_unit
        else:
            return self.pricing_native_unit

    def get_rate_unit_price(self):
        if self.pricing_converted_unit is not None:
            return self.pricing_converted_amount
        else:
            return self.pricing_native_amount

    @property
    def currency(self):
        return self.pricing_unit.currency

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
        uom_conversion_rate = get_uom_conversion_rate(uom_from, uom_to, self.fuel)

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
                           Q(tax__applicable_country=self.supplier_pld_location.location.details.country) |
                           Q(tax_rate_percentage__tax__applicable_country=self.supplier_pld_location.location.details.country),
                           Q(specific_fuel=self.fuel) | Q(specific_fuel__isnull=True),
                           Q(valid_from__lte=self.valid_from_date),
                           Q(Q(valid_to__gte=self.valid_to_date) | Q(valid_ufn=True)),
                           Q(Q(Q(band_1_type_id__in=band_query),
                               Q(band_1_start__lte=self.band_start), Q(band_1_end__gte=self.band_end)) |
                             Q(Q(band_2_type_id__in=band_query),
                               Q(band_2_start__lte=self.band_start), Q(band_2_end__gte=self.band_end)) |
                             Q(Q(band_1_type__isnull=True), Q(band_2_type__isnull=True))
                             ))

        if self.flight_type_id == 'A' and self.destination_type_id == 'ALL':
            qs = TaxRule.objects.filter(common_filters) \
                .exclude(~Q(specific_airport=self.supplier_pld_location.location),
                         Q(specific_airport__isnull=False)) \
                .order_by('id')

            return qs

        elif self.flight_type_id == 'A':
            qs = TaxRule.objects.filter(common_filters,
                                        Q(geographic_flight_type=self.destination_type) |
                                        Q(geographic_flight_type_id='ALL')) \
                .exclude(~Q(specific_airport=self.supplier_pld_location.location),
                         Q(specific_airport__isnull=False)) \
                .order_by('id')

            return qs

        elif self.destination_type_id == 'ALL':
            qs = TaxRule.objects.filter(common_filters,
                                        Q(applicable_flight_type=self.flight_type) |
                                        Q(applicable_flight_type_id='A')) \
                .exclude(~Q(specific_airport=self.supplier_pld_location.location),
                         Q(specific_airport__isnull=False)) \
                .order_by('id')

            return qs

        else:
            qs = TaxRule.objects.filter(common_filters,
                                        Q(applicable_flight_type=self.flight_type) |
                                        Q(applicable_flight_type_id='A'),
                                        Q(geographic_flight_type=self.destination_type) |
                                        Q(geographic_flight_type_id='ALL')) \
                .exclude(~Q(specific_airport=self.supplier_pld_location.location),
                         Q(specific_airport__isnull=False)) \
                .order_by('id')

            return qs

    @property
    def supplier(self):
        return self.supplier_pld_location.pld.supplier

    @property
    def uom(self):
        return self.pricing_unit.uom

    @property
    def pricing_link(self):
        anchor_text = 'Posted Airport Pricing' if getattr(self, 'is_pap', False) else 'Market'

        return f'<a href="{self.url}">{anchor_text}</a>'

    @property
    def specific_handler_link(self):
        if self.specific_handler:
            return f'<a href="{self.specific_handler.get_absolute_url()}">' \
                   f'{self.specific_handler.full_repr}</a>'

    @property
    def url(self):
        return reverse('admin:fuel_pricing_market_documents_pricing_details', kwargs={'pk': self.pk})

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


class FuelPricingMarketReview(models.Model):
    suppliers_fuel_pricing_market = models.ForeignKey("FuelPricingMarket", verbose_name=_("Fuel Pricing Market"),
                                                      on_delete=models.CASCADE, related_name="reviews")
    assigned_at = models.DateTimeField(_("Assigned At"), auto_now=False, auto_now_add=False)
    assigned_to = models.ForeignKey("user.Person", verbose_name=_("Assigned To"),
                                    on_delete=models.RESTRICT, related_name="assigned_fuel_pricing_market_reviews")
    reviewed_at = models.DateTimeField(_("Reviewed At"), auto_now=False, auto_now_add=False,
                                       null=True)
    reviewed_by = models.ForeignKey("user.Person", verbose_name=_("Reviewed By"),
                                    null=True, on_delete=models.RESTRICT,
                                    related_name="reviewed_fuel_pricing_market_reviews")

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_reviews'


class FuelPricingMarketPldQuerySet(models.QuerySet):

    def backlog_entries(self, expired_only=False):
        """
        This query filters out data to be shown in the backlog. Note that the fields must match across
        all involved models, as these are merged using union().
        Also, note that in the future any data provided from a supplier via an integration will need
        to be excluded here, but at the moment no such integrations exist, so this could not be implemented.
        """
        supplier_has_emails = ExpressionWrapper(Exists(OrganisationContactDetails.objects.filter(
            organisation=OuterRef('supplier'), email_address__isnull=False)
        ) | Exists(OrganisationPeople.objects.filter(
            Q(organisation=OuterRef('supplier')) & Q(contact_email__isnull=False)
            & ~Q(contact_email=''))), output_field=BooleanField())

        expiring_pricing = FuelPricingMarket.objects.filter(
            deleted_at__isnull=True, price_active=True, supplier_pld_location__pld=OuterRef('pk')
        )

        if expired_only:
            expiring_pricing = expiring_pricing.filter(valid_to_date__lt=date.today())
        else:
            expiring_pricing = expiring_pricing.filter(
                # Expiring pricing we show in the backlog here depend on length of validity period
                # <= 14 days -> 2 days before expiry
                #  > 14 days -> 5 days before expiry
                Q(valid_to_date__lte=ExpressionWrapper(
                    F('valid_from_date') + timedelta(days=14), output_field=DateField())
                ) & Q(valid_to_date__lte=date.today() + timedelta(days=2)) |
                Q(valid_to_date__gt=ExpressionWrapper(
                    F('valid_from_date') + timedelta(days=14), output_field=DateField())
                ) & Q(valid_to_date__lte=date.today() + timedelta(days=5))
            )

        # Only show PLDs with expiring pricing
        qs = self.filter(Exists(expiring_pricing))

        qs = qs.only('pk', 'priority').annotate(
            type=Value('M'),
            name=F('pld_name'),
            url_pk=F('pk'),
            supplier_pk=F('supplier_id'),
            supplier_name=Case(
                When(supplier__details__trading_name__isnull=False,
                     then=Concat(
                         'supplier__details__trading_name',
                         Value(' ('),
                         'supplier__details__registered_name',
                         Value(')'),
                         output_field=CharField())),
                default=F('supplier__details__registered_name')
            ),
            # Get all locations from related PLD with some non-deleted pricing
            locations_str=StringAgg(
                Concat(
                    F('pld_at_location__location__airport_details__icao_code'),
                    Value(' / '),
                    F('pld_at_location__location__airport_details__iata_code'),
                ),
                delimiter=', ',
                distinct=True,
                filter=Q(Q(pld_at_location__fuel_pricing_market__deleted_at__isnull=True)
                         & Q(pld_at_location__fuel_pricing_market__price_active=True)),
                default=Value('')
            ),
            expiry_date=expiring_pricing.order_by('valid_to_date').values('valid_to_date')[:1],
            supplier_has_emails=supplier_has_emails,
        )

        return qs

    def with_pld_status(self):
        locations = FuelPricingMarketPldLocation.objects.filter(pld_id=OuterRef('id')).with_status()

        is_valid = locations.filter(location_status='OK')
        is_expired = locations.filter(location_status='Expired')
        is_missing = locations.filter(location_status='No Pricing')

        # OK: have valid pricing for all locations, maybe even has expired ones
        # Partial: have valid for some, and invalid for other locations (or a location is missing)
        # Expired: all is invalid

        return self.annotate(
            pld_status=Case(
                When(Q(Q(Exists(is_valid)) & Q(Exists(is_expired))) | Q(Q(Exists(is_valid)) & Q(Exists(is_missing))),
                     then=Value('Partial Pricing Expiry')),
                When(Q(Exists(is_expired)),
                     then=Value('Pricing Expired')),
                When(Q(Exists(is_valid)),
                     then=Value('OK')),
                default=Value('No Pricing'),
                output_field=CharField(max_length=22)
            ))


class FuelPricingMarketPld(PrioritizedModel, PricingBacklogEntry):
    supplier = models.ForeignKey("organisation.Organisation", verbose_name=_("Supplier"),
                                 limit_choices_to=Q(details__type_id__in=[2, 3, 4, 5, 7, 8, 13, 14])
                                                  | Q(airport_details__isnull=False)
                                                  | Q(handler_details__isnull=False) | Q(ipa_details__isnull=False)
                                                  | Q(oilco_details__isnull=False)
                                                  | Q(service_provider_locations__isnull=False),
                                 related_name="fuel_pricing_market_plds_where_is_supplier", on_delete=models.CASCADE)
    pld_name = models.CharField(_("PLD Name"), max_length=255)
    is_current = models.BooleanField(_("Is Current?"), default=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    locations = models.ManyToManyField("organisation.Organisation", verbose_name=_('Locations(s)'),
                                       through='FuelPricingMarketPldLocation', through_fields=('pld', 'location'))

    objects = FuelPricingMarketPldQuerySet.as_manager()

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_pld'
        permissions = [
            (
                "can_supersede_pld",
                "Can supersede the Price List Document to change the 'current' status"
            ),
            (
                "can_alter_pricing_publication_status",
                "Can alter PLD attached pricing publication status"
            )

        ]

    def __str__(self):
        return f'{self.pld_name}'

    @property
    def fuel_types(self):
        pld_locations = self.pld_at_location.all()
        market_entries = FuelPricingMarket.objects.filter(
            Q(supplier_pld_location__in=pld_locations)
            & Q(deleted_at__isnull=True) & Q(price_active=True))

        return market_entries.values_list('fuel__name', flat=True).distinct()

    @property
    def is_published(self):
        locations = FuelPricingMarketPldLocation.objects.filter(pld=self)
        market_entries = FuelPricingMarket.objects.filter(supplier_pld_location__in=locations, price_active=True)
        if not market_entries.exists() or market_entries.filter(is_published=False).exists():
            return False
        else:
            return True

    @property
    def latest_expiry_date(self):
        pld_locations = self.pld_at_location.all()
        market_entries = FuelPricingMarket.objects.filter(
            Q(supplier_pld_location__in=pld_locations)
            & Q(deleted_at__isnull=True) & Q(price_active=True))

        return max(market_entries.values_list('valid_to_date', flat=True).distinct())

    @cached_property
    def location_count(self):
        return self.locations.count()

    def get_fuel_types_at_location(self, location):
        market_entries = FuelPricingMarket.objects.filter(
            Q(supplier_pld_location__pld=self) & Q(supplier_pld_location__location=location)
            & Q(deleted_at__isnull=True) & Q(price_active=True))

        return market_entries.values_list('fuel__name', flat=True).distinct()

    @cached_property
    def locations_billable_orgs(self):
        return list(self.pld_at_location.with_details().values('icao_iata', 'billable_organisation'))

    def locations_billed_by_org_str(self, billable_org):
        billed_locations = list(filter(lambda x: x['billable_organisation'] == billable_org.pk
                                                 or (x['billable_organisation'] is None
                                                 and self.supplier == billable_org),
                                       self.locations_billable_orgs))

        # If the org bills for all locations, we return a simple string
        if len(billed_locations) == self.location_count:
            return 'All locations'

        return ''.join([get_datatable_badge(
            badge_text=loc['icao_iata'],
            badge_class='bg-info datatable-badge-normal badge-multiline badge-250'
        ) for loc in billed_locations])


class FuelPricingMarketPldLocationQueryset(models.QuerySet):
    def with_status(self):
        status_ok = FuelPricingMarket.objects.filter(price_active=True, valid_to_date__gte=datetime.now(),
                                                     supplier_pld_location_id=OuterRef('pk'))

        status_expired = FuelPricingMarket.objects.filter(price_active=True, valid_to_date__lt=datetime.now(),
                                                          supplier_pld_location_id=OuterRef('pk'))

        return self.annotate(
            location_status=Case(
                When(Q(Exists(status_ok)), then=Value('OK')),
                When(Q(Exists(status_expired)), then=Value('Expired')),
                default=Value('No Pricing'),
                output_field=CharField(max_length=1)
            ))

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
            ))


class FuelPricingMarketPldLocation(models.Model):
    pld = models.ForeignKey("FuelPricingMarketPld", verbose_name=_("PLD"),
                            on_delete=models.CASCADE, related_name="pld_at_location")
    location = models.ForeignKey("organisation.Organisation",
                                 limit_choices_to={'details__type_id': 8,
                                                   'airport_details__isnull': False}, verbose_name=_("Location"),
                                 on_delete=models.RESTRICT, related_name="fuel_pricing_market_plds_at_location")
    billable_organisation = models.ForeignKey(
        "organisation.Organisation", verbose_name=_("Billable Organisation"),
        limit_choices_to=Q(details__type_id__in=[2, 3, 4, 5, 7, 8, 9, 13, 14])
                         | Q(airport_details__isnull=False) | Q(handler_details__isnull=False)
                         | Q(ipa_details__isnull=False) | Q(oilco_details__isnull=False)
                         | Q(service_provider_locations__isnull=False),
        on_delete=models.RESTRICT,
        related_name="billed_fuel_pricing_market_pld_locations",
        null=True, blank=True)

    objects = FuelPricingMarketPldLocationQueryset.as_manager()

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_pld_locations'


class FuelPricingMarketPldDocument(models.Model):
    pld = models.ForeignKey('FuelPricingMarketPld', verbose_name=_("PLD"),
                            on_delete=models.CASCADE, related_name='pld_document')
    name = models.CharField(_("Name"), max_length=100)
    description = models.CharField(_("Description"), max_length=500,
                                   null=True, blank=True)
    file = models.FileField(_("Document File"),
                            storage=FuelPricingMarketPldDocumentFilesStorage())

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_pld_documents'


class FuelPricingMarketIncludingTaxes(models.Model):
    pricing = models.ForeignKey("FuelPricingMarket", verbose_name=_("Market Fuel Pricing"),
                                on_delete=models.RESTRICT, related_name='included_taxes',
                                db_column='pricing_market_id')
    tax_category = models.ForeignKey("pricing.TaxCategory", verbose_name=_("Tax Category"),
                                     on_delete=models.RESTRICT, null=True, blank=True)
    applies_to_fees = models.BooleanField(default=False, verbose_name=_("Cascade to Fees?"))

    class Meta:
        db_table = 'suppliers_fuel_pricing_market_inclusive_taxes'
