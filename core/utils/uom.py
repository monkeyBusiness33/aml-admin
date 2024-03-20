from decimal import Decimal
from django.db.models import Q
from core.models import FuelType, PricingUnit, UnitOfMeasurement, UnitOfMeasurementConversionFactor


def get_uom_conversion_rate(uom_from: UnitOfMeasurement, uom_to: UnitOfMeasurement, fuel_type: FuelType):
    if uom_from == uom_to:
        return Decimal(1)

    # Filter from prefetched objects rather than querying the DB each time
    conversion_uom_from = next(filter(lambda x: x.specific_fuel in (None, fuel_type),
                                      sorted(list(uom_from.conversion_factors.all()),
                                             key=lambda x: x.specific_fuel_id)), None)

    conversion_uom_to = next(filter(lambda x: x.specific_fuel in (None, fuel_type),
                                    sorted(list(uom_to.conversion_factors.all()),
                                           key=lambda x: x.specific_fuel_id)), None)

    if not conversion_uom_from:
        raise Exception(f"{fuel_type}: {uom_from} could not be converted into {uom_to}"
                        f" - conversion factor for {uom_from} missing.")

    if not conversion_uom_to:
        raise Exception(f"{fuel_type}: {uom_from} could not be converted into {uom_to}"
                        f" - conversion factor for {uom_to} missing.")

    return conversion_uom_from.conversion_factor_to_litre / conversion_uom_to.conversion_factor_to_litre
