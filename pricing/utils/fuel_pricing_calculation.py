import copy
import json
import random
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby, product
from django.db.models import prefetch_related_objects
from django.conf import settings
from ..models.fuel_agreements_pricing import FuelAgreementPricingFormula, FuelAgreementPricingManual
from ..models.fuel_pricing_market import FuelPricingMarket
from ..models.fuel_fees import SupplierFuelFeeRate
from ..models.tax import TaxRule, TaxRuleException
from ..utils import get_uom_conversion_rate
from aircraft.models import Aircraft, AircraftType
from core.models import Currency, FlightType, FuelCategory, FuelEquipmentType, FuelType, PricingUnit, UnitOfMeasurement
from core.utils.open_xr_api import OpenXRApi
from handling.utils.localtime import get_utc_from_airport_local_time
from organisation.models import Organisation
from organisation.utils.localtime import get_airport_local_time_from_utc


class FuelPricingScenario:
    def __init__(self, airport, form_data, uplift_datetime, is_rerun, xr_overrides):
        self.airport = airport
        self.fuel_cat = form_data['fuel_type']
        self.uplift_qty = form_data['uplift_qty']
        self.uplift_uom = form_data['uplift_uom']
        self.uplift_datetime = uplift_datetime
        self.uplift_time_type = form_data['uplift_time_type']
        self.is_international = form_data['is_international']
        self.applicable_destinations = ['ALL', 'INT' if self.is_international else 'DOM']
        self.flight_type = form_data['flight_type']
        self.applicable_flight_types = ['A'] + (['B', 'G'] if self.flight_type.code in ['B', 'G']
                                                    else [self.flight_type.code])
        self.is_private = form_data['is_private']
        self.currency = form_data['currency']
        self.override_xr = bool(form_data['override_xr'])
        self.xr_overrides = xr_overrides
        self.is_rerun = is_rerun
        self.specific_client = form_data['specific_client']
        self.handler = form_data['handler']
        self.apron = form_data['apron']
        self.overwing_fueling = form_data['overwing_fueling']
        self.is_fuel_taken = form_data['is_fuel_taken']
        self.is_defueling = form_data['is_defueling']
        self.is_multi_vehicle = form_data['is_multi_vehicle']
        self.extend_expired_agreement_client_pricing = form_data['extend_expired_agreement_client_pricing']

        # Prefetch commonly used related objects
        prefetch_related_objects([self.uplift_uom], 'conversion_factors')

        # Get a list of all handlers at location
        self.handlers_at_location = Organisation.objects.handling_agent().filter(
            handler_details__airport=self.airport
        )

        # Determine aircraft type (either type as selected in form, type of selected tail,
        # or a representative type, Gulfstream G650ER, if both fields were left empty)
        self.using_representative_ac_type = False

        if form_data['aircraft_type']:
            self.aircraft_type = form_data['aircraft_type']
        elif form_data['aircraft']:
            self.aircraft_type = form_data['aircraft'].type
        else:
            representative_model = "G650ER"
            self.aircraft_type = AircraftType.objects.filter(model=representative_model).first()
            self.using_representative_ac_type = True

        # Prepare API for currency conversion
        self.open_xr = OpenXRApi(api_key=settings.OPEN_XR_API_KEY)
        self.currency_rates = {}
        self.used_currency_rates = {}

        # Use the date from datetime of uplift converted to UTC (if specified)
        self.datetime_utc = None
        self.date_utc = None

        self.failed_discount_rates = defaultdict(list)

        if self.uplift_datetime is not None and self.uplift_time_type is not None:
            if self.uplift_time_type == 'L':
                self.datetime_utc = get_utc_from_airport_local_time(self.uplift_datetime, self.airport)
            else:
                self.datetime_utc = self.uplift_datetime

            self.date_utc = self.datetime_utc.strftime('%Y-%m-%d')

        # Use provided datetime or current time if absent
        self.validity_datetime_utc = self.datetime_utc or datetime.now().replace(microsecond=0)
        self.validity_datetime_lt = self.uplift_datetime if self.uplift_datetime and self.uplift_time_type == 'L' \
            else get_airport_local_time_from_utc(self.validity_datetime_utc, self.airport)
        self.validity_date_utc = self.validity_datetime_utc.strftime('%Y-%m-%d')

        # Prepare currency exchange API
        self.open_xr = OpenXRApi(api_key=settings.OPEN_XR_API_KEY)

        self.used_plds = set()
        self.used_agreement_ids = set()

    @staticmethod
    def results_collection_row():
        return defaultdict(lambda: {
            'status': 'ok',
            'fuel_price': defaultdict(list, amount=None, agreement_pricing=False, issues=[], notes=[],
                                      currency_rates={}),
            'fees': defaultdict(dict, total=Decimal(0), issues=[], currency_rates={}),
            'taxes': {
                'list': defaultdict(lambda: defaultdict(lambda: defaultdict(dict, amount=Decimal(0), components=[]))),
                'total': Decimal(0),
                'comparison': False,
                'issues': [],
                'currency_rates': {}
            },
            'currency': None,
            'used_currency_rates': {},
            'excluded_delivery_methods': set(),
            'excluded_aprons': set(),
        })

    ##################
    # Fuel Pricing
    ##################

    def get_relevant_fuel_pricing(self):
        """
        Function that gets all entries from `suppliers_fuel_agreements_pricing_formulae`,
        `suppliers_fuel_agreements_pricing_manual` and `suppliers_fuel_pricing_market`
        that are relevant to the given scenario.
        (Agreement pricing overrides any market pricing present)
        """

        # Get formula agreement pricing
        # The field names are different for different classes, so we annotate aliases for consistency
        qs_formula = FuelAgreementPricingFormula.objects.with_archived() \
            .applies_at_location(self.airport) \
            .applies_to_client(self.specific_client) \
            .applies_to_handler(self.handler) \
            .applies_to_apron(self.apron) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_fueling_method(self.overwing_fueling) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_datetime_utc, self.airport,
                                     self.extend_expired_agreement_client_pricing) \
            .with_specificity_score()

        # Also include related models
        qs_formula = qs_formula.select_related(
            'agreement__supplier',
            'differential_pricing_unit__uom',
            'differential_pricing_unit__currency',
            'ipa',
            'pricing_index',
            'specific_handler',
            'specific_apron',
        ).prefetch_related(
            'delivery_methods',
            'differential_pricing_unit__uom__conversion_factors',
        )

        # Get manual agreement pricing
        # The field names are different for different classes, so we annotate aliases for consistency
        qs_manual = FuelAgreementPricingManual.objects.with_archived() \
            .applies_at_location(self.airport) \
            .applies_to_client(self.specific_client) \
            .applies_to_handler(self.handler) \
            .applies_to_apron(self.apron) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_fueling_method(self.overwing_fueling) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_datetime_utc, self.airport,
                                     self.extend_expired_agreement_client_pricing) \
            .with_specificity_score()

        # Also include related models
        qs_manual = qs_manual.select_related(
            'agreement__supplier',
            'ipa',
            'pricing_discount_unit__currency',
            'pricing_discount_unit__uom',
            'specific_handler',
            'specific_apron',
        ).prefetch_related(
            'delivery_methods',
            'pricing_discount_unit__uom__conversion_factors',
        )

        # Get market pricing
        # The field names are different for different classes, so we annotate aliases for consistency
        qs_market = FuelPricingMarket.objects \
            .applies_at_location(self.airport) \
            .applies_to_client(self.specific_client) \
            .applies_to_handler(self.handler) \
            .applies_to_apron(self.apron) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_fueling_method(self.overwing_fueling) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_datetime_utc, self.extend_expired_agreement_client_pricing) \
            .with_specificity_score()

        # Also include related models
        qs_market = qs_market.select_related(
            'ipa',
            'supplier_pld_location__pld__supplier',
            'pricing_native_unit__currency',
            'pricing_native_unit__uom',
            'pricing_converted_unit__currency',
            'pricing_converted_unit__uom',
            'specific_handler',
            'specific_apron',
        ).prefetch_related(
            'delivery_methods',
            'pricing_native_unit__uom__conversion_factors',
            'pricing_converted_unit__uom__conversion_factors',
        )

        all_pricing = list(qs_formula)
        all_pricing.extend(list(qs_manual))
        all_pricing.extend(list(qs_market))

        # Apply quantity bands
        all_rates = [rate for rate in all_pricing if not self.is_fuel_taken
                 or rate.check_band(self.uplift_qty, self.uplift_uom, rate.fuel)]

        # Split out pricing with multiple delivery methods into separate entities
        additional_rates = []

        for rate in all_rates:
            if not rate.delivery_methods.exists():
                rate.delivery_method = None
            else:
                dms = list(rate.delivery_methods.all())
                rate.delivery_method = dms[0]

                for method in dms[1:]:
                    new_rate = copy.deepcopy(rate)
                    new_rate.delivery_method = method
                    additional_rates.append(new_rate)

        all_rates.extend(additional_rates)

        # Sort to prepare for grouping
        all_rates.sort(
            key=lambda x: (x.supplier.id, x.ipa_id or 0, getattr(x.delivery_method, 'pk', 0), x.specific_apron_id or 0))

        # Group by supplier and IPA for initial date filtering
        rates_sup_ipa = {k: list(v) for k, v in groupby(all_rates, lambda x: (x.supplier, x.ipa))}

        # Map supplier-IPA pairs to whether they have valid pricing and latest expiry date
        supplier_ipa_validity = {k: (any([not rate.is_expired for rate in v]),
                                     max([rate.expiry_date if rate.expiry_date else 'UFN' for rate in v]))
                                 for k, v in rates_sup_ipa.items()}

        # Filter out any non-agreement, non-client-specific pricing for each supplier-IPA pair that is
        # - expired, if valid pricing is present for the pair
        # - expired with expiry date older than latest, if no valid pricing present for the pair
        # Expired agreement and client-specific pricing would've been filtered out already, or needs to be extended,
        # depending on setting chosen for extend_expired_agreement_client_pricing
        rates = [rate for rate in all_rates
                 if getattr(rate, 'agreement_id', None) or rate.client_id or not rate.is_expired
                 or (not supplier_ipa_validity[(rate.supplier, rate.ipa)][0]
                     and rate.expiry_date >= supplier_ipa_validity[(rate.supplier, rate.ipa)][1])]

        # Group by supplier, IPA, fuel type, delivery method
        all_prices = groupby(all_rates,
                         lambda x: (
                             x.supplier,
                             x.ipa,
                             x.fuel,
                             x.delivery_method,
                             x.specific_apron
                         ))

        prices = groupby(rates,
                         lambda x: (
                             x.supplier,
                             x.ipa,
                             x.fuel,
                             x.delivery_method,
                             x.specific_apron
                         ))

        prices_dict = self.results_collection_row()

        # Convert to dicts of lists (as we need to access some entries multiple times)
        all_prices = {key: list(group) for (key, group) in all_prices}
        prices = {key: list(group) for (key, group) in prices}

        # Prepare dicts for additional entries
        additional_rows = {}

        # Calculate the amount charged for each pricing
        for supplier, ipa, fuel_type, delivery_method, apron in list(prices.keys()):
            all_rates = all_prices[(supplier, ipa, fuel_type, delivery_method, apron)]
            rates = prices[(supplier, ipa, fuel_type, delivery_method, apron)]
            # Use client-specific pricing over generic pricing, agreement pricing over market pricing,
            # valid pricing over expired, and if no valid pricing present, the pricing with latest expiry,
            # following that pick rate with the highest specificity_score
            rates = sorted(rates,
                           key=lambda x: (
                               getattr(x, 'client_id', None) or 0,
                               getattr(x, 'agreement_id', 0),
                               x.expiry_date or 'UFN',
                               x.specificity_score),
                           reverse=True)
            rate = rates[0]

            pricing_row = prices_dict[(supplier, ipa, fuel_type, delivery_method, apron)]

            # For discount (manual) agreement pricing, also try to find the default market pricing (PAP) to use as base
            # For this we use all_rates, so that expired market rates that would otherwise be dropped can be extended
            if isinstance(rate, FuelAgreementPricingManual):
                rate = self.reconcile_discount_with_market_pricing(rate, supplier, ipa, fuel_type, delivery_method,
                                                                   apron, all_rates, prices, prices_dict,
                                                                   additional_rows)

            if rate is None:
                continue

            self.apply_pricing(pricing_row, rate)

            # For non-handler-specific agreement pricing, try including handler-specific market pricing as well
            if not isinstance(rate, FuelPricingMarket) and not pricing_row['handler_specific_pricing']:
                handler_market_rates = filter(lambda r: isinstance(r, FuelPricingMarket) and r.specific_handler, rates)

                for hm_rate in handler_market_rates:
                    row_key = (supplier, ipa, fuel_type, delivery_method, apron,
                               getattr(hm_rate, 'client', None) is not None, hm_rate.specific_handler)
                    additional_rows[row_key] = hm_rate

            # For client-specific market pricing, try including generic agreement pricing as well for comparison
            if isinstance(rate, FuelPricingMarket) and getattr(rate, 'client_id') is not None:
                agreement_rates = filter(lambda r: getattr(r, 'agreement_id', None), rates)
                agreement_rate = next(agreement_rates, None)

                if agreement_rate and isinstance(agreement_rate, FuelAgreementPricingManual):
                    agreement_rate = self.reconcile_discount_with_market_pricing(
                        agreement_rate, supplier, ipa, fuel_type, delivery_method, apron, all_rates, prices,
                        prices_dict, additional_rows, for_client_spec_market_pricing=True)

                if agreement_rate:
                    row_key = (supplier, ipa, fuel_type, delivery_method, apron, False, agreement_rate.specific_handler)
                    additional_rows[row_key] = agreement_rate

        # Include client-specific (bool) flag and handler in row key
        # (as rows will be distinguished based on that going forward), also apron,
        # Here use the specific apron from input (helps to avoid duplicates later), otherwise always None.
        for k in list(prices_dict.keys()):
            prices_dict[k + (prices_dict[k].get('client_specific_pricing', False),
                             prices_dict[k].get('handler_specific_pricing', None))] = prices_dict[k]
            prices_dict.pop(k)

        # Create additional pricing rows
        for key, rate in additional_rows.items():
            # Skip if client-specfic pricing already exists
            client_specific_key = key[:5] + (True,) + key[6:]
            if client_specific_key in prices_dict and prices_dict[client_specific_key].get(
                'client_specific_pricing', False): continue

            # Leave existing rows, except if they are market pricing and additional row is agreement pricing
            if key not in prices_dict or not isinstance(rate, FuelPricingMarket) \
                and prices_dict[key]['fuel_price']['obj_type'] == 'FuelPricingMarket' :
                prices_dict.pop(key, None)
                pricing_row = prices_dict[key]

                delivery_method = key[3]
                apron = key[4]

                if delivery_method:
                    rate.issues.append(f"The agreement discount pricing covers all delivery methods,"
                                       f" however the market pricing used as base covers only fuel delivered"
                                       f" via <b>{delivery_method}</b>")

                if apron:
                    rate.issues.append(f"The agreement discount pricing covers uplifts from all aprons,"
                                       f" however the market pricing used as base covers only fuel uplifted"
                                       f" from <b>{apron}</b>")

                # When applying client-specific rate, remove corresponding generic rate if exists
                if getattr(rate, 'client_id'):
                    generic_key_start = key[:5] + (False,)

                    for key in list(prices_dict.keys()):
                        if key[:6] == generic_key_start:
                            prices_dict.pop(key, None)

                self.apply_pricing(pricing_row, rate)

        # Filter out any pricing marked as ignored (to be excluded from results)
        prices_dict = {k: v for (k, v) in prices_dict.items() if not v.get('ignore', False)}

        # Add notes to market pricing for supplier+IPA combinations where a discount pricing was available,
        # but was not applied due to delivery method mismatch
        for k, v in prices_dict.items():
            supplier, ipa, fuel_type, delivery_method, apron, client_spec, handler = k

            if (supplier, ipa, fuel_type) in self.failed_discount_rates:
                if getattr(v['fuel_price']['obj'], 'is_pap', False):
                    discount_methods = {r.delivery_method.name for r
                                        in self.failed_discount_rates[(supplier, ipa, fuel_type)] if r.delivery_method}
                    discount_aprons = {r.delivery_method.name for r
                              in self.failed_discount_rates[(supplier, ipa, fuel_type)] if r.specific_apron}

                    v['fuel_price']['issues'].append(f"There is agreement pricing available for this IPA"
                                                     f" and location, applicable to the following "
                                                     + f"delivery methods:"
                                                     + (f" <b>{', '.join(sorted(discount_methods))}</b>,"
                                                        if discount_methods else " <b>All</b> ")
                                                     + "and aprons:"
                                                     + (f" <b>{', '.join(sorted(discount_aprons))}</b>,"
                                                        if discount_aprons else " <b>All</b> ")
                                                     + f" which could not be applied due to "
                                                     + (f"delivery method" if discount_methods else "")
                                                     + ("and" if discount_methods and discount_aprons else "")
                                                     + (f"delivery method" if discount_aprons else "")
                                                     + f" mismatch")

        return prices_dict

    def reconcile_discount_with_market_pricing(self, rate, supplier, ipa, fuel_type, delivery_method, apron, rates,
                                               prices, prices_dict, additional_rows,
                                               for_client_spec_market_pricing=False):

        # Only use PAP as base, also ensure that there is no conflict of specific handler between discount pricing
        # and base pricing (I think we can allow specific + generic, but not two different spec. handlers)
        rate.market_pricing_base = next((r for r in rates if getattr(r, 'is_pap', False)
                                         and (r.specific_handler is None or rate.specific_handler is None
                                              or r.specific_handler == rate.specific_handler)
                                         ), None)

        # If the discount is applicable to a specific delivery method and/or apron, the base has to match or cover all
        # Base with exact match would've already been found, so we only check this when no base found so far
        if delivery_method is not None or apron is not None:
            if rate.market_pricing_base is None:
                # If no matching base found, try to find one applicable to all delivery methods and/or aprons
                market_pricing_matching_apron = prices.get((supplier, ipa, fuel_type, None, apron), [])
                market_pricing_matching_dm = prices.get((supplier, ipa, fuel_type, delivery_method, None), [])
                market_pricing_no_match = prices.get((supplier, ipa, fuel_type, None, None), [])
                market_pricing_for_all_cases = market_pricing_matching_apron + market_pricing_matching_dm \
                                               + market_pricing_no_match

                if market_pricing_for_all_cases:
                    rates = sorted(market_pricing_for_all_cases,
                                   key=lambda x: (
                                       (getattr(x, 'specific_apron_id') or 0) if apron else 0,
                                       getattr(x.delivery_method, 'pk', 0) if delivery_method else 0,
                                       getattr(x, 'agreement_id', 0),
                                       x.expiry_date or 'UFN',
                                       x.specificity_score),
                                   reverse=True)
                    rate.market_pricing_base = next((r for r in rates if getattr(r, 'is_pap', False)), None)

                    # If the market is used as base, remove the market pricing entry altogether
                    if rate.market_pricing_base is not None:
                        base_dm = rate.market_pricing_base.delivery_method
                        base_apron = rate.market_pricing_base.specific_apron
                        prices_dict[(supplier, ipa, fuel_type, base_dm, base_apron)]['ignore'] = True

                        if delivery_method and base_dm is None:
                            rate.issues.append(f"The agreement discount pricing only covers fuel delivered via"
                                               f" <b>{delivery_method.name}</b>, however the market pricing used as base"
                                               f" covers all delivery methods")
                        if apron and base_apron is None:
                            rate.issues.append(f"The agreement discount pricing only covers fuel uplifted from"
                                               f" <b>{apron.name}</b>, however the market pricing used as base"
                                               f" covers all aprons")

        # If the discount covers all in either respect, it can apply to market price
        # with any delivery method / apron, so we need additional rows for each of those cases
        if delivery_method is None or apron is None:
            # Now, the exact subset of market pricing we consider, depends on which of the parameters is None.
            # If only one is None, we only consider rows matching the other one. If both are, we consider all
            # available combinations with higher specificity

            if delivery_method:
                specific_supplier_ipa_pap = {
                    k: [p for p in v if getattr(p, 'is_pap', False)] for (k, v) in prices.items()
                    if (k[0], k[1], k[2]) == (supplier, ipa, fuel_type) and k[3] == delivery_method and k[4] is not None}
            elif apron:
                specific_supplier_ipa_pap = {
                    k: [p for p in v if getattr(p, 'is_pap', False)] for (k, v) in prices.items()
                    if (k[0], k[1], k[2]) == (supplier, ipa, fuel_type) and k[3] is not None and k[4] == apron}
            else:
                specific_supplier_ipa_pap = {
                    k: [p for p in v if getattr(p, 'is_pap', False)] for (k, v) in prices.items()
                    if (k[0], k[1], k[2]) == (supplier, ipa, fuel_type) and k[3] is not None or k[4] is not None}

            for row_key, market_rates in specific_supplier_ipa_pap.items():
                if market_rates:
                    rate_copy = copy.deepcopy(rate)
                    market_rates = sorted(market_rates,
                                          key=lambda x: (
                                              getattr(x, 'agreement_id', 0), x.expiry_date or 'UFN',
                                              x.specificity_score),
                                          reverse=True)
                    rate_copy.market_pricing_base = next(
                        (r for r in market_rates if getattr(r, 'is_pap', False)),
                        None)

                    row_key += (getattr(rate, 'client_id') is not None,
                                prices.get('handler_specific_pricing', None))
                    additional_rows[row_key] = rate_copy

        # If at this point the discount is not viable (no market base), use market pricing instead,
        # or, failing that, discard pricing row altogether. Skip this step if triggered as counterpart
        # for client-specific market rate
        if not for_client_spec_market_pricing and rate.market_pricing_base is None:
            self.failed_discount_rates[(supplier, ipa, fuel_type)].append(rate)

            rate = next((r for r in rates if isinstance(r, FuelPricingMarket)), None)

            if rate is None:
                prices_dict[(supplier, ipa, fuel_type, delivery_method, apron)]['ignore'] = True
                return None

        return rate

    def apply_pricing(self, pricing_row, rate):
        # Add warnings about expired pricing
        if getattr(rate, 'is_expired', False):
            rate.issues.append(f"The fuel pricing data expires before the uplift date "
                               f"(expiry = {rate.expiry_date}). The most recent historical pricing has been used")

        # Add a note about unpublished pricing
        if not rate.is_published:
            rate.notes.append(f"This rate is unpublished")

        pricing_row['client_specific_pricing'] = getattr(rate, 'client_id') is not None

        # Add warning if client-specific discount is based on generic market pricing
        if pricing_row['client_specific_pricing'] and getattr(rate, 'market_pricing_base', None) \
            and getattr(rate.market_pricing_base, 'client_id') is None:
            rate.issues.append(f"The discount pricing is client-specific, however the market pricing used as base"
                               f" is applicable to all clients")

        # Mark handler_specific_pricing
        pricing_row['handler_specific_pricing'] = rate.specific_handler

        if rate.specific_handler:
            rate.notes.append(f"This price only applies when flight is handled by"
                f" <b>{rate.specific_handler.full_repr}</b>")

        # For discount pricing, also treat as handler-specific if the base used is handler-specific
        if not rate.specific_handler and getattr(rate, 'market_pricing_base', None) \
            and rate.market_pricing_base.specific_handler:
            pricing_row['handler_specific_pricing'] = rate.market_pricing_base.specific_handler

            rate.notes.append(f"The base used to calculate this price only applies when flight is handled by"
                              f" <b>{rate.market_pricing_base.specific_handler.full_repr}</b>")

        # Mark apron_specific_pricing
        pricing_row['apron_specific_pricing'] = rate.specific_apron

        if rate.specific_apron:
            rate.notes.append(f"This price only applies when uplift takes place on the"
                f" <b>{rate.specific_apron}</b>")

        # For discount pricing, also treat as apron-specific if the base used is apron-specific
        if not rate.specific_apron and getattr(rate, 'market_pricing_base', None) \
            and rate.market_pricing_base.specific_apron:
            pricing_row['apron_specific_pricing'] = rate.market_pricing_base.specific_apron

            rate.notes.append(f"The base used to calculate this price only applies when uplift takes place on the"
                              f" <b>{rate.market_pricing_base.specific_apron}</b>")

        # Add warning if representative ac type used due to no ac type provided
        if self.using_representative_ac_type:
            rate.issues.append(f"As no aircraft or aircraft type was specified, <b>{self.aircraft_type}</b>"
                               f" was used as an indicative type")

        # Only calculate pricing if fuel uplifted
        amount = self.calculate_pricing(rate, pricing_row) if self.is_fuel_taken else None

        pricing_row['currency'] = self.currency or rate.currency

        pricing_row['fuel_price'] |= {
            'obj_type': type(rate).__name__,
            'pricing_link': rate.pricing_link,
            'base_pricing_url': rate.market_pricing_base.url if getattr(rate, 'market_pricing_base',
                                                                        None) else None,
            'obj': rate,
            'fuel': rate.fuel,
            'amount': amount,
            'unit_price': getattr(rate, 'unit_price', None),
            'original_pricing_unit': getattr(rate, 'pricing_unit', None),
            'converted_uplift_qty': getattr(rate, 'converted_uplift_qty', None),
            'original_currency': rate.currency,
            'agreement_pricing': getattr(rate, 'agreement_id', None) is not None,
            'market_pricing_base': getattr(rate, 'market_pricing_base', None),
            'discount_applied': getattr(rate, 'discount_applied_str', None),
            'uom': rate.uom,
            'issues': rate.issues,
            'notes': rate.notes,
        }

    def calculate_pricing(self, rate, pricing_row):
        price = None

        if isinstance(rate, FuelAgreementPricingFormula):
            # Formula Agreement Pricing

            # Get latest index price
            index_price_obj = rate.pricing_index.prices \
                .filter_by_date_for_calc(self.validity_date_utc) \
                .with_specificity_score(rate.agreement.supplier.pk) \
                .order_by('-specificity_score', '-valid_ufn', '-valid_to').first()

            if not index_price_obj:
                rate.issues.append('Formula agreement pricing was found but no relevant index pricing could be found')
                return

            if not index_price_obj.valid_ufn and index_price_obj.valid_to.strftime("%Y-%m-%d") < self.validity_date_utc:
                rate.issues.append(f"Formula agreement pricing is based on expired index pricing "
                                   f"(expiry = {index_price_obj.valid_to})")
                self.update_pricing_row_status(pricing_row, 'warning')

            # Add a note about unpublished pricing
            if not index_price_obj.is_published:
                rate.notes.append(f"This agreement rate is based on an unpublished fuel index price")

            if index_price_obj.source_organisation != rate.agreement.supplier:
                rate.issues.append(f"Index pricing sourced by <b>{index_price_obj.source_organisation.full_repr}</b> "
                                   f"was used to calculate formula pricing")

            index_price = index_price_obj.price
            index_unit = index_price_obj.pricing_unit

            # Convert index pricing to differential unit
            conversion_factor_diff = self.get_pricing_unit_conversion_rate(
                rate, index_unit, rate.pricing_unit, rate.volume_conversion_ratio_override)
            index_price = (index_price * conversion_factor_diff).quantize(Decimal('0.000001'), ROUND_HALF_UP)

            # Add details of calculation as a note
            rate.notes.insert(0, rate.get_price_calculation_breakdown(index_price_obj, index_price))

            # Add differential to index price to get final unit price
            rate.unit_price = index_price + rate.get_rate_unit_price()

            # Convert uplift unit
            conversion_factor = get_uom_conversion_rate(self.uplift_uom, rate.pricing_unit.uom, rate.fuel)
            rate.converted_uplift_qty = self.uplift_qty / conversion_factor

            price = rate.unit_price * rate.converted_uplift_qty

        elif isinstance(rate, FuelAgreementPricingManual):
            # Manual Agreement Pricing

            # If no market pricing found, the manual agreement pricing can't be calculated
            if not rate.market_pricing_base:
                rate.issues.append('Discount agreement pricing found but market pricing is missing')
                return

            if rate.market_pricing_base.is_expired:
                rate.issues.append(f"Discount agreement pricing is based on expired market pricing "
                                   f"(expiry = {rate.market_pricing_base.valid_to_date})")
                self.update_pricing_row_status(pricing_row, 'warning')

            # Add a note about unpublished pricing
            if not rate.market_pricing_base.is_published:
                rate.notes.append(f"This agreement rate is based on an unpublished market pricing")

            if rate.pricing_discount_amount is not None:
                # Amount-based discount

                # Convert pricing unit to discount unit
                conversion_factor_base = self.get_pricing_unit_conversion_rate(
                    rate,
                    rate.market_pricing_base.pricing_unit,
                    rate.pricing_discount_unit,
                )

                # Apply discount on pricing
                rate.converted_base = rate.market_pricing_base.get_rate_unit_price() * conversion_factor_base
                rate.unit_price = rate.converted_base - rate.pricing_discount_amount

                # Convert uplift unit
                conversion_factor = get_uom_conversion_rate(self.uplift_uom, rate.uom, rate.fuel)
                rate.converted_uplift_qty = self.uplift_qty / conversion_factor

                price = rate.unit_price * rate.converted_uplift_qty
            elif rate.pricing_discount_percentage is not None:
                # Percentage-based discount

                # Apply discount on pricing
                rate.unit_price = rate.get_rate_unit_price() * (1 - rate.pricing_discount_percentage / 100)

                conversion_factor = get_uom_conversion_rate(self.uplift_uom, rate.uom, rate.fuel)
                rate.converted_uplift_qty = self.uplift_qty / conversion_factor
                price = rate.unit_price * rate.converted_uplift_qty

        else:
            # Market Pricing

            rate.unit_price = rate.get_rate_unit_price()

            # For fixed per-uplift price values can be returned directly
            if rate.pricing_unit.uom.code == 'PU':
                price = rate.unit_price
            else:
                # Convert uplift unit
                conversion_factor = get_uom_conversion_rate(self.uplift_uom, rate.pricing_unit.uom, rate.fuel)
                rate.converted_uplift_qty = self.uplift_qty / conversion_factor

                price = rate.unit_price * rate.converted_uplift_qty

        # Convert currencies
        exchange_rate = self.get_currency_xr(rate, rate.currency, self.currency,
                                             curr_from_div=rate.pricing_unit.currency_division_used)
        price /= exchange_rate['rate']

        return price.quantize(Decimal('0.01'), ROUND_HALF_UP)

    ##################
    # Fees
    ##################

    def get_relevant_fuel_fees(self, results):
        """
        Function that gets all entries from `suppliers_fuel_fees_rates`
        that are relevant to the given scenario (with corresponding `suppliers_fuel_fees`)
        """

        # Filter fees applicable to given scenario
        qs = SupplierFuelFeeRate.objects.with_details() \
            .filter_by_source_doc(self.used_plds, self.used_agreement_ids) \
            .applies_for_fuel_taken(self.is_fuel_taken, self.is_defueling) \
            .applies_for_multi_vehicle_uplift(self.is_multi_vehicle) \
            .applies_at_location(self.airport) \
            .applies_to_handler(self.handler) \
            .applies_to_apron(self.apron) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_fueling_method(self.overwing_fueling) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_date_utc) \
            .applies_at_dow_and_time(self.validity_datetime_utc, self.validity_datetime_lt) \
            .with_specificity_score()

        # Also include related models
        qs = qs.select_related(
            'delivery_method',
            'pricing_native_unit__currency',
            'pricing_native_unit__uom',
            'pricing_converted_unit__currency',
            'pricing_converted_unit__uom',
            'specific_apron',
            'specific_handler',
            'supplier_fuel_fee__fuel_fee_category',
            'supplier_fuel_fee__ipa',
            'supplier_fuel_fee__supplier',
        ).prefetch_related(
            'pricing_native_unit__uom__conversion_factors',
            'pricing_converted_unit__uom__conversion_factors',
            'validity_periods',
        )

        # Sort the results
        rates = list(qs.order_by('supplier_fuel_fee__supplier_id', 'supplier_fuel_fee__ipa_id', 'delivery_method',
                                 'supplier_fuel_fee'))

        for rate in rates:
            rate.agreement_pricing = rate.source_agreement is not None

        # Group all combinations of supplier, ipa
        fees = groupby(rates,
                       lambda x: (
                           x.supplier_fuel_fee.supplier,
                           x.supplier_fuel_fee.ipa,
                       ))
        fees = {k: list(v) for k, v in fees}

        # Prepare to collect additional rows that need creation
        additional_rows_from_fees = {}

        # Calculate the amount charged for each fee
        for result_row, pricing_rates in results.items():
            supplier, ipa, fuel_type, delivery_method, apron, client_spec, handler = result_row
            rates = list(fees[(supplier, ipa)]) if (supplier, ipa) in fees else []
            fuel_price_obj = pricing_rates['fuel_price']['obj']

            # Exclude all fees if marked as included in pricing
            _, cascade_to_fees = fuel_price_obj.parent_inclusive_taxes

            if cascade_to_fees:
                continue

            # Filter rates based on source document (only apply agreement rates
            # if the source agreement is also used for fuel pricing, and market rates
            # if the source pld is used for pricing)
            source_pld = fuel_price_obj.supplier_pld_location.pld \
                if hasattr(fuel_price_obj, 'supplier_pld_location') else None
            price_agreement = getattr(fuel_price_obj, 'agreement', None)
            rates = filter(
                lambda r: r.source_agreement == price_agreement or r.supplier_fuel_fee.related_pld == source_pld,
                rates
            )

            # Apply fuel type of the pricing (we run calculation by category,
            # but fees can still be exclusive to given type)
            rates = filter(lambda r: r.specific_fuel in (fuel_price_obj.fuel, None), rates)

            # Apply quantity and weight bands
            # (This had to be moved here as we now specify fuel category rather than type, so we only
            # know the specific fuel type once we know the exact pricing that the fee is applied to)
            rates = filter(
                lambda r: r.check_bands(self.uplift_qty, self.uplift_uom, fuel_price_obj.fuel, self.aircraft_type),
                rates)

            # Filter rates based on dates - we already have rates that are relevant to the specific document
            # and either valid or expired here, so we only need to exclude rates that expired earlier than the pricing
            # (i.e. were archived), effectively we are extending the state from last day of pricing validity.
            pricing_exp_date = fuel_price_obj.expiry_date[:10] if fuel_price_obj.expiry_date else 'UFN'
            rates = filter(lambda r: not r.is_expired or r.expiry_date.strftime("%Y-%m-%d") >= pricing_exp_date, rates)

            # If the pricing is for a specific delivery method, filter rates based on delivery method specified;
            # Rates with specific methods only apply to rows with the same delivery method.
            # Rates without a specific method apply to all rows unless a more specific variant is present
            pricing_delivery_method = getattr(pricing_rates['fuel_price']['obj'], 'delivery_method', None)
            if pricing_delivery_method:
                rates = filter(lambda r: r.delivery_method in [None, pricing_delivery_method], rates)

            # Filter rates based on handler specified for pricing; We can't apply a handler-specific fee on pricing
            # specific for another handler, or if that handler is supposed to be excluded from the fee,
            pricing_handler = pricing_rates.get('handler_specific_pricing', None)
            if pricing_handler:
                rates = filter(
                    lambda r: (not r.specific_handler_is_excluded and r.specific_handler == pricing_handler)
                              or (r.specific_handler_is_excluded and r.specific_handler != pricing_handler)
                              or r.specific_handler is None,
                    rates)

            rates = list(rates)
            all_rates = list(copy.deepcopy(rates))
            pricing_data_before_fees = copy.deepcopy(pricing_rates)

            # Filter rates based on apron specified for pricing; We can't apply an apron-specific fee
            # on pricing specific for another apron.
            pricing_apron = pricing_rates.get('apron_specific_pricing', None)
            if not pricing_apron:
                fee_spec_aprons = {r.specific_apron for r in filter(lambda r: r, all_rates)}

                # Store the aprons with pricing, to list them as exclusions in results table
                pricing_data_before_fees['excluded_aprons'].update({m for m in fee_spec_aprons if m})

                rates = filter(lambda r: r.specific_apron in [None, pricing_apron], rates)

            # For DM-agnostic pricing, fees with specific delivery methods need to be removed,
            # and later used to create DM-specific rows in the results table.
            fee_spec_delivery_methods = {delivery_method}

            if not pricing_delivery_method:
                fee_spec_delivery_methods = {r.delivery_method for r in filter(lambda r: r, all_rates)}

                # Store the methods with pricing, to list them as exclusions in results table
                pricing_data_before_fees['excluded_delivery_methods'].update(
                    {m for m in fee_spec_delivery_methods if m})

                # Remove rates with specific DMs
                rates = filter(lambda r: r.delivery_method is None, rates)

            # If fuel price is not handler-specific, and no handler was selected,
            # check if there are any handler-specific fees
            fee_spec_handlers = {self.handler}

            if not pricing_handler and not self.handler:
                fee_spec_handlers = {r.specific_handler for r in filter(lambda r: r, all_rates)}

                # In this case, I believe we have to remove all specific fees from general pricing, as otherwise
                # They'd overlap with the specific rows, and also if there are fees from multiple handlers,
                # we obviously can't just apply them all. We should keep the ones excluding the specific handler though.
                # (this is subject to change based on feedback)
                rates = filter(lambda r: r.specific_handler is None or r.specific_handler_is_excluded, rates)

            # Analogously, if no apron was selected, check if there are any apron-specific fees
            fee_spec_aprons = {self.apron}

            if not self.apron:
                fee_spec_aprons = {r.specific_apron for r in filter(lambda r: r, all_rates)}

                # In this case, I believe we have to remove all specific fees from general pricing, as otherwise
                # They'd overlap with the specific rows, and also if there are fees for multiple spec. aprons,
                # we obviously can't just apply them all.
                rates = filter(lambda r: r.specific_apron is None, rates)

            # Group rates by fee
            rates_by_fee = groupby(rates,
                                   lambda x: (
                                       x.supplier_fuel_fee.local_name
                                   ))

            # Use rate with the highest specificity_score for each fee (if any)
            for fee_name, rates in rates_by_fee:
                self.apply_fee(fee_name, rates, pricing_rates)

            # CREATE ADDITIONAL ROWS FOR HANDLER-/APRON-SPECIFIC FEES

            # If pricing is generic in either aspect, and there are handler- or apron-specific fees available,
            # create a new pricing row for each combination (except where a row already exists)
            new_rows_handler_apron = list(product(fee_spec_delivery_methods, fee_spec_handlers, fee_spec_aprons))

            # Sort the more general cases to be considered first (helps with deduplication later)
            new_rows_handler_apron = sorted(new_rows_handler_apron,
                                            key=lambda k: (getattr(k[0], 'pk', 0),
                                                           getattr(k[1], 'pk', 0),
                                                           getattr(k[2], 'pk', 0)))

            # Update the exclusion lists for original row as well
            pricing_rates['excluded_delivery_methods'] \
                = copy.copy(pricing_data_before_fees['excluded_delivery_methods'])
            pricing_rates['excluded_aprons'] \
                = copy.copy(pricing_data_before_fees['excluded_aprons'])

            for delivery_method, handler, apron in new_rows_handler_apron:
                # The handler component of the key needs to also consider if the pricing is not already
                # handler/apro specific, otherwise we'll get confusing duplicates
                handler_for_key = pricing_data_before_fees['handler_specific_pricing'] or handler
                apron_for_key = pricing_data_before_fees['apron_specific_pricing'] or apron
                pricing_key = (supplier, ipa, fuel_type, delivery_method, apron_for_key, client_spec, handler_for_key)

                if pricing_key in results:
                    # For existing pricing row, update excluded delivery methods and aprons and skip insertion
                    results[pricing_key]['excluded_delivery_methods'] \
                        = copy.copy(pricing_data_before_fees['excluded_delivery_methods'])
                    results[pricing_key]['excluded_aprons'] \
                        = copy.copy(pricing_data_before_fees['excluded_aprons'])

                    continue

                if pricing_key not in additional_rows_from_fees:
                    additional_rows_from_fees[pricing_key] = {
                        'pricing_data': copy.deepcopy(pricing_data_before_fees),
                        'applicable_fee_rates': copy.deepcopy(all_rates),
                    }

        # Keep track of newly added fees (pks and totals) - to remove those that make no difference
        # Also consider fees for the original rows here as starting point
        added_fees_per_row = defaultdict(list)

        for row_key in results:
            general_key = (*row_key[:4], row_key[5])
            fees_applied = results[row_key]['fees']['list'].keys()
            fees_total = Decimal(sum(v['amount'] for v in results[row_key]['fees']['list'].values()))

            added_fees_per_row[general_key].append((fees_applied, fees_total))

        # Process all the additional rows created from dm-/handler-/apron-specific fees
        for row_key, row_data in additional_rows_from_fees.items():

            supplier, ipa, fuel_type, delivery_method, apron, client_spec, handler = row_key
            pricing_data, rates = row_data.values()

            # Create a new row in results
            results[row_key] = pricing_data

            # Mark the pricing as handler-/apron-specific where applicable
            if handler:
                pricing_data['handler_specific_pricing'] = handler

            if apron:
                pricing_data['apron_specific_pricing'] = apron

            # Filter rates based on specific DM, handler and/or apron
            rates = filter(lambda r: ((not r.specific_handler_is_excluded and r.specific_handler == handler)
                                      or (r.specific_handler_is_excluded and r.specific_handler != handler)
                                      or r.specific_handler is None)
                                     and r.delivery_method in [None, delivery_method]
                                     and r.specific_apron in [None, apron], rates)
            rates = list(rates)

            # Group rates by fee
            rates_by_fee = groupby(rates,
                                   lambda x: (
                                       x.supplier_fuel_fee.local_name
                                   ))

            # Use rate with the highest specificity_score for each fee (if any)
            for fee_name, rates in rates_by_fee:
                self.apply_fee(fee_name, rates, pricing_data)

            # For rows generated for handler-/apron-specific pricing, check against existing rows
            # and don't insert if the exact same pricing exists for a more general case
            general_key = (*row_key[:4], row_key[5])
            fees_applied = results[row_key]['fees']['list'].keys()
            fees_total = Decimal(sum(v['amount'] for v in results[row_key]['fees']['list'].values()))

            if (fees_applied, fees_total) not in added_fees_per_row[general_key]:
                # Remember only general or semi-general cases
                if None in [apron, handler]:
                    added_fees_per_row[general_key].append((fees_applied, fees_total))
            else:
                results.pop(row_key)


        # Get totals for each table row (combination of supplier, ipa, fuel type and delivery method)
        for table_row in results:
            row_total = Decimal(sum(v['amount'] for v in results[table_row]['fees']['list'].values()))
            row_agreement_pricing = any([v['agreement_pricing'] for v in results[table_row]['fees']['list'].values()])

            results[table_row]['fees']['agreement_pricing'] = row_agreement_pricing
            results[table_row]['fees']['total'] = row_total.quantize(Decimal('0.01'), ROUND_HALF_UP)

        return dict(results)

    def apply_fee(self, fee_name, rates, pricing_rates):
        rates = sorted(rates, key=lambda x: x.specificity_score, reverse=True)
        rate = rates[0] if rates else None

        if rate is None:
            return

        # Add warnings about expired pricing
        if getattr(rate, 'is_expired', False):
            rate.notes.append(f"This fee expires before the uplift date (expiry = {rate.expiry_date}). "
                              f"The most recent historical pricing has been used")

        if not rate.is_published:
            rate.notes.append(f"This fee is based on an unpublished agreement")

        if rate.specific_handler:
            if rate.specific_handler_is_excluded:
                rate.notes.append(f"This fee only applies when flight is NOT handled by"
                                  f" <b>{rate.specific_handler.full_repr}</b>")
            else:
                # Make sure the row is marked if any explicitly handler-specific fees are included
                pricing_rates['handler_specific_pricing'] = rate.specific_handler
                rate.notes.append(f"This fee only applies when flight is handled by"
                                  f" <b>{rate.specific_handler.full_repr}</b>")

        if rate.specific_apron:
            pricing_rates['apron_specific_pricing'] = rate.specific_apron
            rate.notes.append(f"This fee only applies when uplift takes place on the"
                              f" <b>{rate.specific_apron}</b>")

        # Use global currency override, if none then use any previously recorded currency
        currency_override = pricing_rates['currency']
        amount = self.calculate_fee(rate, self.currency or currency_override, pricing_rates['fuel_price']['obj'])

        # If no override previously recorded, use the currency as override
        if not currency_override:
            pricing_rates['currency'] = self.currency or rate.currency

        if amount is not None:
            fee = rate.supplier_fuel_fee
            pricing_rates['fees']['currency_rates'] |= rate.currency_rates

            pricing_rates['fees']['list'][fee.pk] = {
                'obj_type': type(rate).__name__,
                'obj': rate,
                'amount': amount,
                'unit_price': getattr(rate, 'unit_price', None),
                'converted_uplift_qty': getattr(rate, 'converted_uplift_qty', None),
                'original_pricing_unit': getattr(rate, 'pricing_unit', None),
                'original_currency': rate.currency,
                'agreement_pricing': rate.agreement_pricing,
                'uom': rate.uom,
                'display_name': fee.display_name,
                'notes': rate.notes,
            }

    def calculate_fee(self, rate, currency_override, fuel_price_obj):
        rate.unit_price = rate.get_unit_price()

        # For fixed fees values can be returned directly
        if rate.pricing_unit.uom.code == 'PU':
            price = rate.unit_price
        else:
            # Convert uplift unit
            conversion_factor = get_uom_conversion_rate(self.uplift_uom, rate.pricing_unit.uom, fuel_price_obj.fuel)
            rate.converted_uplift_qty = self.uplift_qty / conversion_factor

            price = rate.unit_price * rate.converted_uplift_qty

        # Convert currencies
        exchange_rate = self.get_currency_xr(rate, rate.pricing_unit.currency, currency_override,
                                             curr_from_div=rate.pricing_unit.currency_division_used)
        price /= exchange_rate['rate']

        return price.quantize(Decimal('0.01'), ROUND_HALF_UP)

    ##################
    # Taxes
    ##################

    def get_supplier_taxes(self):
        """
        Function that filters out all entries from `taxes_rules_exceptions`
        that are relevant to the given fuel pricing scenario
        """
        # Filter taxes applicable to given scenario
        qs = TaxRuleException.objects.with_details() \
            .filter_by_source_doc(self.used_plds, self.used_agreement_ids) \
            .applies_for_fuel_taken(self.is_fuel_taken) \
            .applies_to_fuel_or_fees() \
            .applies_for_fuel_taken(self.is_fuel_taken) \
            .applies_on_date(self.validity_date_utc) \
            .applies_at_location(self.airport) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_date_utc) \
            .with_specificity_score()

        # Also include related models
        qs = qs.select_related(
            'exception_organisation',
            'tax',
            'tax_application_method__fuel_pricing_unit__uom',
            'tax_application_method__fuel_pricing_unit__currency',
            'taxable_tax__tax',
            'taxable_tax__tax_rate_percentage__tax',
            'taxable_exception__tax',
        ).prefetch_related(
            'tax_application_method__fuel_pricing_unit__uom__conversion_factors',
        )

        # Sort the results
        supplier_tax_exceptions = list(qs.order_by('exception_organisation_id', 'tax_id'))

        supplier_tax_rules_dict = {}

        for tax, exceptions in groupby(supplier_tax_exceptions, lambda x: (x.exception_organisation, x.tax)):
            supplier_tax_rules_dict[tax] = list(exceptions)

        return supplier_tax_rules_dict

    def get_official_taxes(self):
        """
        Function that filters out all entries from `taxes_rules`
        that are relevant to the given fuel pricing scenario
        """
        # Filter taxes applicable to given scenario
        qs = TaxRule.objects.with_details() \
            .applies_to_fuel_or_fees() \
            .applies_for_fuel_taken(self.is_fuel_taken) \
            .applies_on_date(self.validity_date_utc) \
            .applies_at_location(self.airport) \
            .applies_to_fuel_cat(self.fuel_cat) \
            .applies_to_destination(self.applicable_destinations) \
            .applies_to_flight_type(self.applicable_flight_types) \
            .applies_to_commercial_private(self.is_private) \
            .filter_by_date_for_calc(self.validity_date_utc) \
            .with_specificity_score()

        # Also include related models
        qs = qs.select_related(
            'tax',
            'tax_application_method__fuel_pricing_unit__uom',
            'tax_application_method__fuel_pricing_unit__currency',
            'tax_rate_percentage__tax',
            'taxable_tax__applicable_flight_type',
            'taxable_tax__tax',
            'taxable_tax__tax_rate_percentage'
        ).prefetch_related(
            'tax_application_method__fuel_pricing_unit__uom__conversion_factors',
        )

        # Sort the results
        official_tax_rules = list(qs.order_by('parent_tax'))

        # Group taxes by parent tax
        official_tax_rules_dict = {}

        # For each tax, if airport-specific rules exist, drop the country-specific ones
        for tax, rules_for_tax in groupby(official_tax_rules, lambda x: x.parent_tax_obj):
            rules_for_tax = list(rules_for_tax)
            airport_specific_rules = list(filter(lambda x: x.specific_airport is not None, rules_for_tax))
            official_tax_rules_dict[tax] = airport_specific_rules if len(airport_specific_rules) else rules_for_tax

        return official_tax_rules_dict

    def apply_taxes(self, pricing_row, pricing, taxes):
        supplier, ipa, fuel_type, delivery_method, apron, client_spec, handler = pricing_row
        fuel_price_obj = pricing['fuel_price']['obj']

        for row in taxes:
            if isinstance(row[0], tuple):
                (exception_organisation, tax), rules = row

                # Supplier taxes only apply on pricing for that supplier (matched based on exception_organisation_id)
                if exception_organisation != supplier:
                    continue

                # Filter supplier tax rates based on source document (only apply agreement rates
                # if the source agreement is also used for fuel pricing, and market rates
                # if the source pld is used for pricing)
                source_pld = fuel_price_obj.supplier_pld_location.pld \
                    if hasattr(fuel_price_obj, 'supplier_pld_location') else None
                price_agreement = getattr(fuel_price_obj, 'agreement', None)
                rules = filter(
                    lambda r: r.source_agreement == price_agreement or r.related_pld == source_pld,
                    rules
                )
            else:
                tax, rules = row

            # Exclude tax categories included in pricing
            excluded_cats, _ = fuel_price_obj.parent_inclusive_taxes

            included_in_pricing = 'A' in excluded_cats or tax.category_id in excluded_cats

            # Apply fuel type of the pricing (we run calculation by category,
            # but taxes can still be exclusive to given type, which should then match the type of pricing)
            rules = filter(lambda r: r.specific_fuel in (fuel_price_obj.fuel, None)
                                     and r.specific_fuel_cat in (self.fuel_cat, None), rules)

            # Apply bands (again, we can only do this once we know fuel type of pricing)
            rules = filter(lambda r: r.check_bands(self, fuel_price_obj.fuel), rules)

            # Filter rates based on dates - we already have rates that are relevant to the specific document
            # (for supplier taxes) and either valid or expired here, so we only need to exclude rates that expired
            # earlier than the pricing (i.e. were archived), effectively we are extending the state from last day
            # of pricing validity.
            pricing_exp_date = fuel_price_obj.expiry_date[:10] if fuel_price_obj.expiry_date else 'UFN'
            rules = filter(lambda r: not r.is_expired or r.expiry_date.strftime("%Y-%m-%d") >= pricing_exp_date,
                           rules)

            # Convert to list so that the list can be used as filtering base multiple times
            rules = list(rules)

            # Apply tax on fuel

            # Filter relevant rules and use the one with the highest specificity_score
            fuel_rules = list(filter(lambda x: x.applies_to_fuel, rules))

            if fuel_rules:
                fuel_rules = sorted(fuel_rules, key=lambda x: (x.specific_fuel_id or 0,
                                                               x.specific_fuel_cat_id or 0,
                                                               x.specificity_score),
                                    reverse=True)
                applicable_rule = fuel_rules[0]
                tax_base = pricing['fuel_price']['amount']

                if not included_in_pricing:
                    amount = self.calculate_tax(pricing, tax, applicable_rule, tax_base)
                else:
                    amount = Decimal('0.0000')

                if amount is not None and amount > 0 or included_in_pricing:
                    self.add_tax_to_pricing(pricing, tax, amount, applicable_rule, inc_in_pricing=included_in_pricing,
                                            base_component={'fuel': True})

            # Apply tax on each fee
            for fee, fee_dict in pricing['fees']['list'].items():
                # Filter relevant rules and use the one with the highest specificity_score
                # (Match fee cat. + only percentage-based taxes can apply on services)
                cat_id = fee_dict['obj'].supplier_fuel_fee.fuel_fee_category_id
                fee_rules = list(filter(
                    lambda x: x.applies_to_fees and x.specific_fee_category_id in [cat_id, None] and x.percentage,
                    rules
                ))

                if not fee_rules:
                    continue

                fee_rules = sorted(fee_rules, key=lambda x: (x.specific_fee_category_id or 0, x.specificity_score),
                                   reverse=True)
                applicable_rule = fee_rules[0]
                tax_base = fee_dict['amount']

                if not included_in_pricing:
                    amount = self.calculate_tax(pricing, tax, applicable_rule, tax_base)
                else:
                    amount = Decimal('0.0000')

                base_fee_cat = fee_dict['obj'].supplier_fuel_fee.fuel_fee_category_id
                applicable_rule.base_fee_cat = base_fee_cat

                if amount is not None and amount > 0 or included_in_pricing:
                    self.add_tax_to_pricing(pricing, tax, amount, applicable_rule, add_to_existing=True,
                                            inc_in_pricing=included_in_pricing,
                                            base_component={'fees': [fee_dict['obj'].supplier_fuel_fee.display_name]})

        # Apply taxes on all taxes that finally apply on each side
        # (based on APC implementation, only percentage-based taxes can be applied
        # this way, and it only goes one level deep).
        for base_tax in pricing['taxes']['list'].copy():
            for tax_source in ['official', 'supplier']:
                if tax_source not in pricing['taxes']['list'][base_tax]:
                    continue

                base_rule = pricing['taxes']['list'][base_tax][tax_source]

                for base_rule_dict in iter(base_rule['components']):
                    taxable_rule = base_rule_dict['obj'].taxable

                    if not taxable_rule or not taxable_rule.percentage:
                        continue

                    # Check if flight type and destination apply (as in APC), also spec. fuel and fee cat
                    if (taxable_rule.geographic_flight_type_id not in self.applicable_destinations or
                        taxable_rule.applicable_flight_type_id not in self.applicable_flight_types or
                        taxable_rule.specific_fuel_id not in [None, fuel_price_obj.fuel.pk] or
                        getattr(taxable_rule.specific_fuel, 'category_id', None) not in [None, self.fuel_cat.pk] or
                        taxable_rule.specific_fuel_cat_id not in [None, self.fuel_cat.pk] or
                        taxable_rule.specific_fee_category_id not in [None, base_rule_dict['base_fee_cat']]):
                        continue

                    taxable_rule.base = base_rule_dict['amount']
                    amount = self.calculate_tax(pricing, taxable_rule.parent_tax_obj, taxable_rule, taxable_rule.base)

                    if amount is not None and amount > 0:
                        self.add_tax_to_pricing(pricing, taxable_rule.parent_tax_obj, amount, taxable_rule,
                                                source_override=tax_source, add_to_existing=True,
                                                base_component={'taxes': [base_tax]})

        # Get totals (overall total based on supplier taxes if present, official taxes otherwise)
        pricing['taxes']['official_total'] = Decimal(sum(v['official']['amount']
                                                         for v in pricing['taxes']['list'].values()
                                                         if 'official' in v)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        pricing['taxes']['supplier_total'] = Decimal(sum(v['supplier']['amount']
                                                         for v in pricing['taxes']['list'].values()
                                                         if 'supplier' in v)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        pricing['taxes']['total'] = pricing['taxes']['supplier_total'] or pricing['taxes']['official_total']

        # Set flag to indicate whether both types of tax need to be compared (and add relevant issue)
        if pricing['taxes']['official_total'] != pricing['taxes']['supplier_total']:
            self.update_pricing_row_status(pricing, 'warning')
            pricing['taxes']['comparison'] = True
            pricing['taxes']['issues'].append("The supplier-defined tax rates are different to the official rates")

        # Compare the values of each tax to determine how the tax will be highlighted
        for row in pricing['taxes']['list'].values():
            if 'supplier' in row and 'official' in row and row['supplier']['amount'] == row['official']['amount']:
                row_highlight_class = 'tax-highlight-match'
            else:
                row_highlight_class = 'tax-highlight-diff'

            row['row_highlight_class'] = row_highlight_class

    def calculate_tax(self, pricing, tax, applicable_rule, tax_base):
        amount = None

        if applicable_rule.percentage is not None:
            # Percentage-based tax
            # If no correct base present, percentage-based taxes cannot be calculated
            if tax_base is None:
                return amount

            applicable_rule.base = tax_base
            amount = applicable_rule.base * applicable_rule.percentage / 100
        elif applicable_rule.tax_unit_rate and applicable_rule.tax_application_method:
            if applicable_rule.tax_application_method.fuel_pricing_unit:
                # Uplift-based tax
                applicable_rule.pricing_unit = applicable_rule.tax_application_method.fuel_pricing_unit

                if applicable_rule.pricing_unit.uom.code == 'PU':
                    # For fixed fees values can be returned directly
                    amount = applicable_rule.tax_unit_rate
                else:
                    # Convert uplift unit
                    conversion_factor = get_uom_conversion_rate(
                        self.uplift_uom,
                        applicable_rule.tax_application_method.fuel_pricing_unit.uom,
                        pricing['fuel_price']['obj'].fuel
                    )
                    applicable_rule.converted_uplift_qty = self.uplift_qty / conversion_factor

                    amount = applicable_rule.tax_unit_rate * applicable_rule.converted_uplift_qty

                # Convert currencies
                currency = applicable_rule.tax_application_method.fuel_pricing_unit.currency
                exchange_rate = self.get_currency_xr(applicable_rule, currency, pricing['currency'],
                                                     curr_from_div=applicable_rule.pricing_unit.currency_division_used)
                amount /= exchange_rate['rate']
                # applicable_rule.tax_unit_rate /= exchange_rate
            elif applicable_rule.tax_application_method.fixed_cost_application_method:
                # Fixed cost tax
                # This is not implemented for now (not applicable to fuel pricing or fees in current version)
                pass
        else:
            pricing['taxes']['issues'].append(
                f"The tax {'rule' if isinstance(applicable_rule, TaxRule) else 'exception'} "
                f"{applicable_rule} ({tax}) has no percentage or unit rate.")

        if amount is not None:
            return amount.quantize(Decimal('0.01'), ROUND_HALF_UP)

    def add_tax_to_pricing(self, pricing, tax, amount, applicable_rule, source_override=None, add_to_existing=False,
                           inc_in_pricing=False, base_component=None):

        pricing['taxes']['currency_rates'] |= applicable_rule.currency_rates

        tax_dict = {
            'obj_type': type(applicable_rule).__name__,
            'obj': applicable_rule,
            'amount': amount,
            'unit_price': getattr(applicable_rule, 'tax_unit_rate', None),
            'base': getattr(applicable_rule, 'base', None),
            'base_fee_cat': getattr(applicable_rule, 'base_fee_cat', None),
            'percentage': getattr(applicable_rule, 'percentage', None),
            'converted_uplift_qty': getattr(applicable_rule, 'converted_uplift_qty', None),
            'uom': applicable_rule.tax_application_method.fuel_pricing_unit.uom \
                if getattr(applicable_rule.tax_application_method, 'fuel_pricing_unit', None) else None,
            'original_pricing_unit': getattr(applicable_rule, 'pricing_unit', None),
            'original_currency': applicable_rule.currency or pricing['fuel_price']['original_currency'],
            'inc_in_pricing': inc_in_pricing,
            'base_components': base_component,
        }

        if isinstance(applicable_rule, TaxRule) and source_override != 'supplier':
            self.add_component_to_tax(pricing['taxes']['list'][tax.local_name], tax_dict,
                                      amount, 'official', add_to_existing)

        # Official tax rates also apply on supplier side, unless they get overwritten by supplier tax later,
        # or unless the tax is explicitly meant to apply on official side only
        if source_override != 'official':
            self.add_component_to_tax(pricing['taxes']['list'][tax.local_name], tax_dict,
                                      amount, 'supplier', add_to_existing)

    @staticmethod
    def add_component_to_tax(tax, component_dict, amount, source, add_to_existing=False):
        if add_to_existing:
            tax[source]['amount'] += amount
            tax[source]['components'].append(component_dict.copy())
        else:
            tax[source]['amount'] = amount
            tax[source]['components'] = [component_dict.copy()]

    def get_results(self):
        """
        A function that collects all relevant fuel prices, fees and taxes for the give scenario
        and returns the charges for each, including the total, as well as any caution messages.
        """
        # Get relevant pricing
        results = self.get_relevant_fuel_pricing()

        # Collect all used source documents for pre-filtering
        self.used_plds = set(results[r]['fuel_price']['obj'].supplier_pld_location.pld.pk for r in results
                             if hasattr(results[r]['fuel_price']['obj'], 'supplier_pld_location'))
        self.used_agreement_ids = set(results[r]['fuel_price']['obj'].agreement.pk for r in results
                                      if hasattr(results[r]['fuel_price']['obj'], 'agreement'))

        # Get relevant fees
        results = self.get_relevant_fuel_fees(results)

        # Get sets of applicable supplier and official taxes
        official_taxes = self.get_official_taxes()
        supplier_taxes = self.get_supplier_taxes()

        # Apply taxes on fuel prices (official taxes should always come first
        # as they may be overwritten by supplier taxes, but not the other way around)
        taxes_list = list(official_taxes.items()) + list(supplier_taxes.items())
        for k, v in results.items():
            self.apply_taxes(k, v, taxes_list)

        # Sort by ascending totals
        final_results = []

        for row, pricing in results.items():
            supplier, ipa, fuel_type, delivery_method, client_spec, handler, apron = row

            # If any of the totals are missing, mark calculation as failed
            if not pricing['fuel_price']['amount']:
                self.update_pricing_row_status(pricing, 'error')
                pricing['fuel_price']['issues'].append(f"No fuel pricing calculated for this scenario")

            if not pricing['fees']['total']:
                self.update_pricing_row_status(pricing, 'error')
                pricing['fees']['issues'].append(f"No fees calculated for this scenario")

            if not pricing['taxes']['total']:
                self.update_pricing_row_status(pricing, 'error')
                pricing['taxes']['issues'].append(f"No taxes calculated for this scenario")

            # Leave out rows without fuel pricing, unless calculation scenario is without uplift,
            # in which case include any rows with fees (those will be no fuel / defueling fees)
            if pricing['fuel_price']['amount'] is not None or not self.is_fuel_taken and pricing['fees']['list']:
                # Add a note about unmodeled included taxes
                inc_taxes = pricing['fuel_price']['obj'].inclusive_taxes_str

                if inc_taxes and not inc_taxes.startswith('All'):
                    inc_taxes = set(inc_taxes.split(', '))
                    tax_rates = [v['official']['components'] + v['supplier']['components'] \
                                 for k, v in pricing['taxes']['list'].items()]
                    taxes = [comp['obj'].tax or comp['obj'].parent_tax_obj for tax in tax_rates for comp in tax]
                    tax_cats = {tax.category.name for tax in taxes}
                    inc_taxes = ', '.join(inc_taxes.difference(tax_cats))

                    if inc_taxes:
                        pricing['fuel_price']['issues'].append(f"This supplier has stated that <b>{inc_taxes}</b>"
                                                               f" is included in the fuel product pricing, however"
                                                               f" there are no applicable rules in the database"
                                                               f" for these taxes")

                final_results.append({
                    'key': str(random.getrandbits(16)),
                    'airport': self.airport,
                    'supplier': supplier,
                    'ipa': ipa,
                    'fuel_type': fuel_type,
                    'delivery_method': delivery_method,
                    'excluded_delivery_methods': pricing.get('excluded_delivery_methods', None),
                    'excluded_aprons': pricing.get('excluded_aprons', None),
                    'client_specific_pricing': pricing['client_specific_pricing'],
                    'handler_specific_pricing': {
                        'pk': pricing['handler_specific_pricing'].pk,
                        'name': pricing['handler_specific_pricing'].full_repr,
                    } if pricing['handler_specific_pricing'] else None,
                    'apron_specific_pricing': {
                        'pk': pricing['apron_specific_pricing'].pk,
                        'name': pricing['apron_specific_pricing'].name,
                    } if pricing['apron_specific_pricing'] else None,
                    'agreement_pricing': pricing['fuel_price']['agreement_pricing'] if pricing['fuel_price'] else False,
                    'currency': ({
                        'code': pricing['currency'].code,
                        'symbol': pricing['currency'].symbol,
                        'division_name': pricing['currency'].division_name,
                        'division_factor': pricing['currency'].division_factor
                    }) if pricing['currency'] else None,
                    'fuel_price': pricing['fuel_price'],
                    'fees': pricing['fees'],
                    'taxes': pricing['taxes'],
                    'total_official_taxes': (pricing['fuel_price']['amount'] if pricing['fuel_price'][
                        'amount'] else Decimal(0))
                                            + pricing['fees']['total']
                                            + pricing['taxes']['official_total'],
                    'total': (pricing['fuel_price']['amount'] if pricing['fuel_price']['amount'] else Decimal(0))
                             + pricing['fees']['total']
                             + pricing['taxes']['total'],
                    'issues': pricing['fuel_price']['issues']
                              + pricing['fees']['issues']
                              + pricing['taxes']['issues'],
                    'status': pricing['status'],
                    'used_currency_rates': pricing['fuel_price']['obj'].currency_rates |
                                           pricing['fees']['currency_rates'] |
                                           pricing['taxes']['currency_rates']
                })

        final_results = sorted(final_results, key=lambda x: x['total'])

        if final_results:
            final_results[0]['additional_classes'] = 'results-least-expensive'

        return final_results

    def update_pricing_row_status(self, pricing_row, new_status):
        """
        Update status of the pricing row to a stronger one (ERROR > WARNING > OK),
        but not the other way around. All rows start with 'ok' status as default.
        """
        statuses = ['ok', 'warning', 'error']
        new_status = new_status.lower()

        if new_status not in statuses:
            raise Exception('Invalid status passed to update_pricing_row_status.')

        if pricing_row['status'] in statuses and statuses.index(pricing_row['status']) >= statuses.index(new_status):
            return

        pricing_row['status'] = new_status

    def get_currency_xr(self, rate, curr_from, curr_to, curr_from_div=False, curr_to_div=False):
        # If second currency not provided, default to keeping same currency, but still account for currency division
        if curr_to is None:
            curr_to = curr_from

        # If base (target) currency was not used before, get the set of rates for it
        if curr_to.code not in self.currency_rates:
            self.currency_rates[curr_to.code] = self.open_xr.get_exchange_rates(curr_to.code, self.date_utc)

        # Get rate for given currency pair
        if curr_from != curr_to:
            if self.override_xr and self.is_rerun:
                curr_xr = self.xr_overrides[(curr_from.code, curr_to.code)].copy()
            else:
                curr_xr = {
                    'rate': Decimal(self.currency_rates[curr_to.code]['rates'][curr_from.code]).quantize(
                        Decimal('0.000001'), ROUND_HALF_UP),
                    'src': 'OXR',
                    'timestamp': self.currency_rates[curr_to.code]['timestamp']
                }

            self.used_currency_rates[(curr_from.code, curr_to.code)] = curr_xr.copy()
            rate.currency_rates[(curr_from.code, curr_to.code)] = curr_xr.copy()
        else:
            curr_xr = {
                'rate': Decimal(1),
                'src': None,
                'timestamp': None,
            }

        # Apply currency divisions
        if curr_from_div:
            curr_xr['rate'] *= curr_from.division_factor
        if curr_to_div:
            curr_xr['rate'] /= curr_to.division_factor

        return curr_xr

    def get_pricing_unit_conversion_rate(self, rate, pu_from: PricingUnit, pu_to: PricingUnit,
                                         volume_rate_override: Decimal = None) -> Decimal:
        if pu_from == pu_to:
            return Decimal(1)

        # Get uom component
        uom_conversion_factor = volume_rate_override or get_uom_conversion_rate(pu_from.uom, pu_to.uom, rate.fuel)

        # Get currency component
        currency_xr = self.get_currency_xr(rate, pu_from.currency, pu_to.currency, pu_from.currency_division_used,
                                           pu_to.currency_division_used)

        return uom_conversion_factor / currency_xr['rate']

    def serialize(self):
        excluded_field_names = ['open_xr', 'currency_rates', 'xr_overrides', 'failed_discount_rates',
                                'handlers_at_location']
        return ResultsSerializer().serialize(self.__dict__, excluded_field_names)


class ResultsSerializer:
    def serialize(self, obj, excluded_field_names=()):
        if isinstance(obj, datetime):
            return self.serialize(obj.strftime('%Y-%m-%d %H:%M:%S'))
        if isinstance(obj, date):
            return self.serialize(obj.strftime('%Y-%m-%d'))
        if isinstance(obj, list):
            return [self.serialize(el) for el in obj]
        if isinstance(obj, set):
            return [self.serialize(el) for el in list(obj)]
        elif isinstance(obj, dict):
            return {self.serialize(k): self.serialize(v) for k, v in obj.items() if k not in excluded_field_names}
        elif isinstance(obj, tuple):
            return json.dumps(obj)
        elif type(obj) in [Decimal, datetime]:
            return str(obj)
        elif isinstance(obj, Aircraft):
            return {
                'pk': obj.pk,
                'details': {
                    'registration': obj.details.registration
                }
            }
        elif isinstance(obj, AircraftType):
            return {
                'pk': obj.pk
            }
        elif isinstance(obj, FlightType):
            return {
                'code': obj.code,
                'name': obj.name
            }
        elif isinstance(obj, Currency):
            return {
                'pk': obj.pk,
                'code': obj.code,
                'symbol': obj.symbol,
                'division_name': obj.division_name,
                'division_factor': obj.division_factor
            }
        elif isinstance(obj, FuelEquipmentType):
            return {
                'pk': obj.pk,
                'name': obj.name
            }
        elif isinstance(obj, Organisation):
            return {
                'pk': obj.pk,
                'full_repr': obj.full_repr
            }
        elif isinstance(obj, UnitOfMeasurement):
            return {
                'pk': obj.pk,
                'code': obj.code,
                'description': obj.description,
                'description_plural': obj.description_plural,
            }
        elif isinstance(obj, PricingUnit):
            return {
                'pk': obj.pk,
                'description': obj.description,
                'description_short': obj.description_short,
                'currency_division_used': obj.currency_division_used
            }
        elif isinstance(obj, FuelType):
            return {
                'pk': obj.pk,
                'name': obj.name
            }
        elif isinstance(obj, FuelCategory):
            return {
                'pk': obj.pk,
                'name': obj.name
            }
        elif isinstance(obj, FuelPricingMarket):
            return {
                'pk': obj.pk,
                'amount': self.serialize(obj.pricing_native_amount),
                'pricing_unit': self.serialize(obj.pricing_unit)
            }
        elif getattr(obj, 'pk', None):
            return obj.pk
        else:
            return obj
