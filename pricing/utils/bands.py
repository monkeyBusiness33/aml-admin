from aircraft.models import AircraftWeightUnit
from core.utils.uom import get_uom_conversion_rate
from core.models.uom import UnitOfMeasurement


def check_fuel_band_overlap(band_1_uom, band_1_start, band_1_end, band_2_uom, band_2_start, band_2_end, fuel_type):
    '''
    This function returns False if a pair of fuel bands has no overlap.
    If there is overlap or any of the band units is None, it returns True.
    '''
    if band_1_uom is None or band_2_uom is None:
        return True

    # If bands have different units, conversion needed
    if band_1_uom != band_2_uom:
        conversion_rate = get_uom_conversion_rate(band_2_uom, band_1_uom, fuel_type)

        if conversion_rate:
            band_2_start /= conversion_rate
            band_2_end /= conversion_rate

    return band_1_start <= band_2_end and band_2_start <= band_1_end


def check_fuel_band(band_uom, band_start, band_end, quantity, quantity_uom, fuel_type):
    '''
    This function returns False if quantity is outside the fuel band.
    If quantity falls within band or the band unit is None, it returns True.
    '''
    if band_uom is None:
        return True

    # If no uplift unit provided, no actual fuel band can apply
    if quantity_uom is None:
        return False

    # If different units, conversion needed
    if band_uom != quantity_uom:
        conversion_rate = get_uom_conversion_rate(quantity_uom, band_uom, fuel_type)

        if conversion_rate:
            quantity /= conversion_rate

    return band_start <= quantity <= band_end


def check_weight_band(ac_type, band_type, band_start, band_end):
    '''
    This function checks if aircraft type is within the specified weight band.
    Returns True if the band unit is None or aircraft weight is inside band limits.
    '''
    if band_type is None:
        return True

    # For fees, the weight band links directly to AircraftWeightUnit
    if isinstance(band_type, AircraftWeightUnit):
        ac_weight = ac_type.mtow_indicative_kg if '(kg' in band_type.name else ac_type.mtow_indicative_lbs
    # For taxes, the `charge_bands` table is used
    else:
        ac_weight = ac_type.mtow_indicative_kg if 'mtow_kg' in band_type.reference else ac_type.mtow_indicative_lbs

    if ac_weight is None:
        return True

    return band_start <= ac_weight <= band_end


def check_band(pricing_scenario, fuel_type, band_type, band_start, band_end):
    '''
    This function checks if the pricing scenario matches the specified band.
    Returns True if there is no band (type is None) or relevant parameter is within band limits.
    Returns False if band not implemented yet or the relevant parameter is outside band limits.
    '''
    if band_type is None:
        return True

    if band_type.type == 'FU':
        band_unit_code = 'USG' if band_type.reference == '$fuel_uplift_usg' else 'L'
        band_uom = UnitOfMeasurement.objects.filter(code=band_unit_code).first()

        return check_fuel_band(band_uom, band_start, band_end, pricing_scenario.uplift_qty,
                               pricing_scenario.uplift_uom, fuel_type)
    if band_type.type == 'WB':
        ac_type = pricing_scenario.aircraft_type

        return check_weight_band(ac_type, band_type, band_start, band_end)
    else:
        return False

    return band_start <= quantity <= band_end
