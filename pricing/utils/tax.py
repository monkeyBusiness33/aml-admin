from django import forms
from ..utils.fuel_pricing_market import normalize_fraction, find_decimals, get_band_tolerance
from ..models.tax import TaxRule, TaxRuleException
from datetime import date
from decimal import Decimal

def check_overlap_with_existing_taxes(form, rule, form_data, valid_ufn, context):
    '''
    Used for official taxes, checks if the created/edited tax overlaps with existing taxes, as to not make duplicates
    '''

    flight_type = form_data.get('applicable_flight_type')
    geographic_flight_type = form_data.get('geographic_flight_type')
    specific_fuel = form_data.get('specific_fuel')
    specific_fuel_cat = form_data.get('specific_fuel_cat')
    specific_fee_category = form_data.get('specific_fee_category')
    applies_to_fees = form_data.get('applies_to_fees')
    applies_to_fuel = form_data.get('applies_to_fuel')
    band_1_type = form_data.get('band_1_type')
    band_2_type = form_data.get('band_2_type')

    geographic_overlaps = False
    type_overlaps = False
    specific_fuel_overlaps = False
    specific_fee_category_overlaps = False
    band_1_overlaps = False
    band_2_overlaps = False
    band_1_uom_overlaps = False
    band_2_uom_overlaps = False
    bands_swapped = False
    condition_one_missing = False
    condition_two_missing = False

    if rule.applicable_flight_type.name != str(flight_type):
         return
    else:
        type_overlaps = True

    if str(geographic_flight_type) == rule.geographic_flight_type.name:
        geographic_overlaps = True

    if applies_to_fuel and rule.applies_to_fuel:
        # There's only overlap if both fuel-specific fields match
        # (either both are None or the selected one is the same in both cases)
        if str(specific_fuel) == str(rule.specific_fuel) \
            and str(specific_fuel_cat) == str(rule.specific_fuel_cat):
            specific_fuel_overlaps = True

    if applies_to_fees and rule.applies_to_fees and\
        str(specific_fee_category) == str(rule.specific_fee_category):

         specific_fee_category_overlaps = True

    if getattr(band_1_type, 'type', lambda: 'No band 1') == getattr(rule.band_2_type, 'type', lambda: 'No rule band 1') or\
        getattr(band_2_type, 'type', lambda: 'No band 2') == getattr(rule.band_1_type, 'type', lambda: 'No rule band 2'):
         band_1_type, band_2_type = band_2_type, band_1_type
         bands_swapped = True

    # Raw band type overlap
    if band_1_type is not None and (band_1_type == rule.band_1_type or band_1_type == rule.band_2_type):
        band_1_overlaps = True

    # UOM Overlap
    if 'kg' in str(band_1_type) and 'lbs' in str(rule.band_1_type) or\
        'lbs' in str(band_1_type) and 'kg' in str(rule.band_1_type) or\
        'litres' in str(band_1_type) and 'usg' in str(rule.band_1_type) or\
        'usg' in str(band_1_type) and 'litres' in str(rule.band_1_type):
            band_1_uom_overlaps = True

    if band_2_type is not None and (band_2_type == rule.band_2_type or band_2_type == rule.band_1_type):
        band_2_overlaps = True

    if 'kg' in str(band_2_type) and 'lbs' in str(rule.band_2_type) or\
        'lbs' in str(band_2_type) and 'kg' in str(rule.band_2_type) or\
        'litres' in str(band_2_type) and 'usg' in str(rule.band_2_type) or\
        'usg' in str(band_2_type) and 'litres' in str(rule.band_2_type):
            band_2_uom_overlaps = True

    # Bands (if present) can clear the other ones, if they are unique (but not the other band!)
    if band_1_type is not None and band_2_type is not None and\
       (not band_1_overlaps and not band_1_uom_overlaps and not band_2_overlaps and not band_2_uom_overlaps):
        geographic_overlaps = False
        type_overlaps = False
        specific_fuel_overlaps = False
        specific_fee_category_overlaps = False

    if not specific_fuel_overlaps and not specific_fee_category_overlaps:
        geographic_overlaps = False
        type_overlaps = False
        band_1_overlaps = False
        band_2_overlaps = False
        band_1_uom_overlaps = False
        band_2_uom_overlaps = False

    if not geographic_overlaps:
        specific_fuel_overlaps = False
        specific_fee_category_overlaps = False
        type_overlaps = False
        band_1_overlaps = False
        band_2_overlaps = False
        band_1_uom_overlaps = False
        band_2_uom_overlaps = False

    if rule.band_1_type is not None and (rule.band_1_type != band_1_type and rule.band_1_type != band_2_type):
        condition_one_missing = True

    if rule.band_2_type is not None and (rule.band_2_type != band_1_type and rule.band_1_type != band_2_type):
        condition_two_missing = True

    if any([geographic_overlaps, type_overlaps, specific_fuel_overlaps, specific_fee_category_overlaps,
            band_1_overlaps, band_2_overlaps, band_1_uom_overlaps, band_2_uom_overlaps,
            condition_one_missing, condition_two_missing]):

        generate_form_errors(form, geographic_overlaps, type_overlaps, specific_fuel_overlaps,
                             specific_fee_category_overlaps, band_1_overlaps, band_2_overlaps,
                             band_1_uom_overlaps, band_2_uom_overlaps, bands_swapped, valid_ufn,
                             condition_one_missing, condition_two_missing, band_1_type, band_2_type, context)

        return True
    else:
        return False


def generate_form_errors(form, geographic_overlaps, type_overlaps, specific_fuel_overlaps,
                         specific_fee_category_overlaps, band_1_overlaps, band_2_overlaps, band_1_uom_overlaps,
                         band_2_uom_overlaps, bands_swapped, valid_ufn, condition_one_missing, condition_two_missing,
                         band_1_type, band_2_type, context):

    if type_overlaps:
        form.add_error(f'applicable_flight_type', "An existing tax overlaps or matches this field's value")

    if geographic_overlaps:
        form.add_error(f'geographic_flight_type', "An existing tax overlaps or matches this field's value")

    if specific_fuel_overlaps:
        specific_fuel = form.cleaned_data.get('specific_fuel')
        specific_fuel_cat = form.cleaned_data.get('specific_fuel_cat')

        if specific_fuel:
            form.add_error(f'specific_fuel', "An existing tax overlaps or matches this field's value")

        if specific_fuel_cat:
            form.add_error(f'specific_fuel_cat', "An existing tax overlaps or matches this field's value")

        if not any([specific_fuel, specific_fuel_cat]):
            form.add_error(f'specific_fuel', "An existing tax overlaps or matches this field's value")
            form.add_error(f'specific_fuel_cat', "An existing tax overlaps or matches this field's value")

    if specific_fee_category_overlaps:
        form.add_error(f'specific_fee_category', "An existing tax overlaps or matches this field's value")

    if band_1_overlaps:
        if bands_swapped:
            form.add_error(f'band_2_type', "An existing tax's condition overlaps with this condition")
        else:
            form.add_error(f'band_1_type', "An existing tax's condition overlaps with this condition")

    if band_1_uom_overlaps:
        if bands_swapped:
            form.add_error(f'band_2_type', "An existing tax's condition unit overlaps with this condition")
        else:
            form.add_error(f'band_1_type', "An existing tax's condition unit overlaps with this condition")

    if band_2_overlaps:
        if bands_swapped:
            form.add_error(f'band_1_type', "An existing tax's condition overlaps with this condition")
        else:
            form.add_error(f'band_2_type', "An existing tax's condition overlaps with this condition")

    if band_2_uom_overlaps:
        if bands_swapped:
            form.add_error(f'band_1_type', "An existing tax's condition unit overlaps with this condition")
        else:
            form.add_error(f'band_2_type', "An existing tax's condition unit overlaps with this condition")

    if condition_one_missing:
        if band_2_type is None:
            form.add_error(f'band_2_type', "Missing a condition that applies to an existing tax")
        else:
            form.add_error(f'band_1_type', "Missing a condition that applies to an existing tax")

    if condition_two_missing:
        if band_1_type is None:
            form.add_error(f'band_1_type', "Missing a condition that applies to an existing tax")
        else:
            form.add_error(f'band_2_type', "Missing a condition that applies to an existing tax")

    # Add these errors regardless
    form.add_error('applies_to_private', '')
    form.add_error('applies_to_commercial', '')
    form.add_error('applies_to_fuel', '')
    form.add_error('applies_to_fees', '')
    form.add_error('pax_must_stay_aboard', '')
    form.add_error('waived_for_tech_stop', '')
    form.add_error('valid_from', '')
    if valid_ufn:
        form.add_error('valid_ufn', '')
    else:
        if context == 'official':
            form.add_error('valid_to', '')

    if any([type_overlaps, geographic_overlaps, specific_fuel_overlaps, specific_fee_category_overlaps]):
        message = f'New tax collides with an existing tax rule.'
        note = f'Note that in certain cases, changing one field solves all other matches or overlaps.'
        if message not in str(form.errors):
            form.add_error(None, message)
            form.add_error(None, note)


def crosscheck_with_taxable_taxes(form, has_band_pricing, instances_of_band_1, instances_of_band_2, taxable_tax,
                                  context, form_number, skip_errors=False):
    '''
    Used to check if the selected 'Official Tax' or 'Supplier-defined Tax' can apply to the created/edited official tax
    or supplier-defined tax
    '''

    band_1_type = form.cleaned_data.get('band_1_type')
    band_2_type = form.cleaned_data.get('band_2_type')
    flight_type = form.cleaned_data.get('applicable_flight_type')
    geographic_flight_type = form.cleaned_data.get('geographic_flight_type')
    specific_fuel = form.cleaned_data.get('specific_fuel')
    specific_fuel_cat = form.cleaned_data.get('specific_fuel_cat')
    specific_fee_category = form.cleaned_data.get('specific_fee_category')
    applies_to_fees = form.cleaned_data.get('applies_to_fees')
    applies_to_fuel = form.cleaned_data.get('applies_to_fuel')
    applies_to_private = form.cleaned_data.get('applies_to_private')
    applies_to_commercial = form.cleaned_data.get('applies_to_commercial')
    valid_from = form.cleaned_data.get('valid_from')
    pax_stays = form.cleaned_data.get('pax_must_stay_aboard')
    tech_stop = form.cleaned_data.get('waived_for_tech_stop')
    specific_airport = form.cleaned_data.get('specific_airport')

    taxable_tax_chosen = taxable_tax
    child_entries = taxable_tax_chosen.child_entries.all().order_by('band_1_start', 'band_2_start')

    if context == 'official':
        all_entries = TaxRule.objects.filter(id = taxable_tax.id).union(child_entries)
    else:
        all_entries = TaxRuleException.objects.filter(id = taxable_tax.id).union(child_entries)

    if context == 'official':
        taxable_name = 'VAT'
    else:
        taxable_name = 'exception VAT'

    has_mismatch = False
    replace_bands = False
    has_extra_condition_one_rows = False
    has_extra_condition_two_rows = False
    has_band_type_errors = False

    if context == 'official':
        if form.cleaned_data.get('valid_ufn'):
            valid_ufn = True
            valid_to = date(9999, 12, 31)
        else:
            valid_to = form.cleaned_data.get('valid_to')
            valid_ufn = False
    else:
        # Note: we can check for exception vs. official matching but their validity will change during supersede
        valid_ufn = True
        valid_to = date(9999, 12, 31)

    # Check if selected airport matches a region (for region based taxable taxes)
    if specific_airport and getattr(taxable_tax_chosen.tax_rate_percentage.tax, 'applicable_region') is not None:
        if specific_airport.airport_details.region.name != taxable_tax_chosen.tax_rate_percentage.tax.applicable_region.name:
            has_mismatch = True
            if not skip_errors:
                form.add_error('taxable_tax', f'The selected airport is not located in the\
                                "{taxable_tax_chosen.tax_rate_percentage.tax.applicable_region.name}" region')

    if not (flight_type == taxable_tax_chosen.applicable_flight_type or taxable_tax_chosen.applicable_flight_type.code == 'A'):
        has_mismatch = True
        if not skip_errors:
            form.add_error('applicable_flight_type', f'Mismatch with the selected {taxable_name}')

    if not (geographic_flight_type == taxable_tax_chosen.geographic_flight_type or taxable_tax_chosen.geographic_flight_type.code == 'ALL'):
        has_mismatch = True
        if not skip_errors:
            form.add_error('geographic_flight_type', f'Mismatch with the selected {taxable_name}')

    if not (specific_fuel == taxable_tax_chosen.specific_fuel or taxable_tax_chosen.specific_fuel is None):
        has_mismatch = True
        if not skip_errors:
            form.add_error('specific_fuel', f'Mismatch with the selected {taxable_name}')

    if not (specific_fuel_cat == taxable_tax_chosen.specific_fuel_cat or taxable_tax_chosen.specific_fuel_cat is None):
        has_mismatch = True
        if not skip_errors:
            form.add_error('specific_fuel_cat', f'Mismatch with the selected {taxable_name}')

    if not (specific_fee_category == taxable_tax_chosen.specific_fee_category or taxable_tax_chosen.specific_fee_category is None):
        has_mismatch = True
        if not skip_errors:
            form.add_error('specific_fee_category', f'Mismatch with the selected {taxable_name}')

    # Note: if we have a primary tax that applies to fuel, services, private, commercial etc...
    # We can still apply that, because 1. this can be interpreted as an override 2. less data entry needed for every case
    # (e.g.: we don't need to specify a primary VAT for tech stop, non tech stop, pax stays, pax disembarks)
    # Hence we have '... or >>condition<<'
    if not (applies_to_fuel == taxable_tax_chosen.applies_to_fuel or taxable_tax_chosen.applies_to_fuel):
        has_mismatch = True
        if not skip_errors:
            form.add_error('applies_to_fuel', f'Mismatch with the selected {taxable_name}')

    if not (applies_to_fees == taxable_tax_chosen.applies_to_fees or taxable_tax_chosen.applies_to_fees):
        has_mismatch = True
        if not skip_errors:
            form.add_error('applies_to_fees', f'Mismatch with the selected {taxable_name}')

    if not (applies_to_private == taxable_tax_chosen.applies_to_private or taxable_tax_chosen.applies_to_private):
        has_mismatch = True
        if not skip_errors:
            form.add_error('applies_to_private', f'Mismatch with the selected {taxable_name}')

    if not (applies_to_commercial == taxable_tax_chosen.applies_to_commercial or taxable_tax_chosen.applies_to_commercial):
        has_mismatch = True
        if not skip_errors:
            form.add_error('applies_to_commercial', f'Mismatch with the selected {taxable_name}')

    if not (pax_stays == taxable_tax_chosen.pax_must_stay_aboard or taxable_tax_chosen.pax_must_stay_aboard):
        has_mismatch = True
        if not skip_errors:
            form.add_error('pax_must_stay_aboard', f'Mismatch with the selected {taxable_name}')

    if not (tech_stop == taxable_tax_chosen.waived_for_tech_stop or taxable_tax_chosen.waived_for_tech_stop):
        has_mismatch = True
        if not skip_errors:
            form.add_error('waived_for_tech_stop', f'Mismatch with the selected {taxable_name}')

    if not valid_from:
        has_mismatch = True
        if not skip_errors:
            form.add_error('valid_from', '')
    else:
        if not (valid_from >= taxable_tax_chosen.valid_from):
            has_mismatch = True
            if not skip_errors:
                form.add_error('valid_from', f'Mismatch with the selected {taxable_name}')

    if context == 'official' and valid_to is not None:
        if taxable_tax_chosen.valid_to is not None:
            if not (valid_to <= taxable_tax_chosen.valid_to):
                has_mismatch = True
                if not skip_errors:
                    form.add_error('valid_to', f'Mismatch with the selected {taxable_name}')

        elif not (valid_ufn == taxable_tax_chosen.valid_ufn or taxable_tax_chosen.valid_ufn):
            has_mismatch = True
            if not skip_errors:
                form.add_error('valid_to', f'Mismatch with the selected {taxable_name}')

    if taxable_tax_chosen.band_1_type is not None or taxable_tax_chosen.band_2_type is not None:

        if band_1_type is None and band_2_type is None:
            has_band_type_errors = True
            if not skip_errors:
                raise forms.ValidationError(f'Cannot apply tax as it would apply more broadly than the selected {taxable_name}')

        if band_1_type == taxable_tax_chosen.band_2_type and band_2_type == taxable_tax_chosen.band_1_type:
            band_1_type, band_2_type = band_2_type, band_1_type
            replace_bands = True

        if band_1_type != taxable_tax_chosen.band_1_type and band_1_type != taxable_tax_chosen.band_2_type:
            if band_1_type is None:
                if band_1_type == taxable_tax_chosen.band_1_type:
                    has_band_type_errors = True
                    if not skip_errors:
                        raise forms.ValidationError(f'Cannot apply tax as the selected {taxable_name}\'s second condition\
                                                    applies more broadly')
                else:
                    has_band_type_errors = True
                    if not skip_errors:
                        raise forms.ValidationError(f'Cannot apply tax as the selected {taxable_name}\'s first condition\
                                                    applies more broadly')
            else:
                if band_2_type != taxable_tax_chosen.band_1_type and band_2_type != taxable_tax_chosen.band_2_type:
                    has_band_type_errors = True
                    if not skip_errors:
                        form.add_error(f'band_1_type', '')
                        form.add_error(f'band_2_type', '')
                        raise forms.ValidationError(f'Condition Types does not match against the selected {taxable_name}\'s\
                                                    Condition Types')
                else:
                    has_band_type_errors = True
                    if not skip_errors:
                        form.add_error(f'band_1_type', '')
                        raise forms.ValidationError(f'Condition One Type does not match against the selected {taxable_name}\'s\
                                                    Condition Types')

        if band_2_type != taxable_tax_chosen.band_1_type and band_2_type != taxable_tax_chosen.band_2_type:
            if band_2_type is None:
                if band_1_type != taxable_tax_chosen.band_1_type:
                    has_band_type_errors = True
                    if not skip_errors:
                        raise forms.ValidationError(f'Cannot apply tax as the selected {taxable_name}\'s first condition\
                                                    applies more broadly')
                else:
                    has_band_type_errors = True
                    if not skip_errors:
                        raise forms.ValidationError(f'Cannot apply tax as the selected {taxable_name}\'s second condition\
                                                    applies more broadly')
            else:
                if band_1_type != taxable_tax_chosen.band_1_type and band_1_type != taxable_tax_chosen.band_2_type:
                    has_band_type_errors = True
                    if not skip_errors:
                        form.add_error(f'band_1_type', '')
                        form.add_error(f'band_2_type', '')
                        raise forms.ValidationError(f'Condition Types does not match against the selected {taxable_name}\'s\
                                                    Condition Types')
                else:
                    has_band_type_errors = True
                    if not skip_errors:
                        form.add_error(f'band_2_type', '')
                        raise forms.ValidationError(f'Condition Two Type does not match against the selected {taxable_name}\'s\
                                                    Condition Types')

        # On supersede, return when a band type error is encountered
        if has_band_type_errors and skip_errors:
            return True

        # We can apply the taxable tax even without bands
        if band_1_type and child_entries.count() == 0:
            return has_mismatch

        elif band_2_type and child_entries.count() == 0:
            return has_mismatch

        # With bands, we have to check if their start and end range match (e.g.: 1-999999)
        if has_band_pricing:
            taxable_tax_band_1_start = taxable_tax_chosen.band_1_start
            taxable_tax_band_1_end = child_entries[len(child_entries)-1].band_1_end
            taxable_tax_band_2_start = taxable_tax_chosen.band_2_start
            taxable_tax_band_2_end = child_entries[len(child_entries)-1].band_2_end

            entry_band_1_start = form.cleaned_data.get('band_1_start')
            entry_band_1_end = form.cleaned_data.get(f'band_1_end-additional-{form_number}-{instances_of_band_1 - 1}')
            entry_band_2_start = form.cleaned_data.get('band_2_start')
            entry_band_2_end = form.cleaned_data.get(f'band_2_end-additional-{form_number}-{instances_of_band_2 - 1}')

            band_range_error = False
            if band_1_type:
                if taxable_tax_band_1_start != entry_band_1_start:
                    band_range_error = True
                    if not skip_errors:
                        form.add_error('band_1_start', '')
                if taxable_tax_band_1_end < entry_band_1_end:
                    band_range_error = True
                    if not skip_errors:
                        form.add_error(f'band_1_end-additional-{form_number}-{instances_of_band_1 - 1}', '')

            if band_2_type:
                if taxable_tax_band_2_start != entry_band_2_start:
                    band_range_error = True
                    if not skip_errors:
                        form.add_error('band_2_start', '')

                if taxable_tax_band_2_end < entry_band_2_end:
                    band_range_error = True
                    if not skip_errors:
                        form.add_error(f'band_2_end-additional-{form_number}-{instances_of_band_2 - 1}', '')

            if band_range_error:
                if not skip_errors:
                    raise forms.ValidationError(f'Mismatch with the selected {taxable_name}\'s condition range(s)')
                else:
                    return True

            # Check if the taxable tax is more "detailed" than the one we create (e.g.: it has 1-250 / 251-500 bands
            # while the one we create has a 1-500 band)
            if instances_of_band_1 != child_entries.count() or instances_of_band_2 != child_entries.count():
                row_number = 0
                for field, value in list(form.cleaned_data.items()):
                    if 'band_1_start' in field:
                        if replace_bands:
                            band_2_start = value
                        else:
                            band_1_start = value
                        continue

                    if 'band_1_end' in field:
                        if replace_bands:
                            band_2_end = value
                        else:
                            band_1_end = value
                        continue

                    if 'band_2_start' in field:
                        if replace_bands:
                            band_1_start = value
                        else:
                            band_2_start = value
                        continue

                    if 'band_2_end' in field:
                        if replace_bands:
                            band_1_end = value
                        else:
                            band_2_end = value

                        if band_1_start is not None:
                            for entry in all_entries:
                                if (band_1_end - band_1_start > entry.band_1_end - entry.band_1_start) and\
                                    entry.band_1_end <= band_1_end and entry.band_1_start >= band_1_start:
                                    has_extra_condition_one_rows = True
                                    if row_number == 0:
                                        if not skip_errors:
                                            form.add_error('band_1_start', '')
                                            form.add_error('band_1_end', '')
                                    else:
                                        if not skip_errors:
                                            form.add_error(f'band_1_start-additional-{form_number}-{row_number}', '')
                                            form.add_error(f'band_1_end-additional-{form_number}-{row_number}', '')
                                    break

                        if band_2_start is not None:
                            for entry in all_entries:
                                if (band_2_end - band_2_start > entry.band_2_end - entry.band_2_start) and\
                                    entry.band_2_end <= band_2_end and entry.band_2_start >= band_2_start:
                                    has_extra_condition_two_rows = True
                                    if row_number == 0:
                                        if not skip_errors:
                                            form.add_error('band_2_start', '')
                                            form.add_error('band_2_end', '')
                                    else:
                                        if not skip_errors:
                                            form.add_error(f'band_2_start-additional-{form_number}-{row_number}', '')
                                            form.add_error(f'band_2_end-additional-{form_number}-{row_number}', '')
                                    break

                        row_number += 1

    if has_extra_condition_one_rows:
        if not skip_errors:
            form.add_error(None, f'The selected {taxable_name}\'s first condition would apply different rates to the\
                                   highlighted band row(s)')
        else:
            return True

    if has_extra_condition_two_rows:
        if not skip_errors:
            form.add_error(None, f'The selected {taxable_name}\'s second condition would apply different rates to the\
                                   highlighted band row(s)')
        else:
            return True

    return has_mismatch


def taxrule_label_from_instance(obj):
    '''
    Used to display 'Official Taxes' (% based) for the taxable tax dropdown
    '''

    if obj is None:
        return ''

    if obj.tax_rate_percentage.tax.short_name:
        name = f'{obj.tax_rate_percentage.tax.local_name} ({obj.tax_rate_percentage.tax.short_name})'
    else:
        name = f'{obj.tax_rate_percentage.tax.local_name}'

    region_or_airport = ''
    if obj.tax_rate_percentage.tax.applicable_region:
        region_or_airport = f'in {obj.tax_rate_percentage.tax.applicable_region.name}'
    elif obj.specific_airport:
        region_or_airport = f'at {obj.specific_airport.airport_details.icao_iata}'

    rate = f'- {obj.tax_rate_percentage.tax_percentage}%'

    validity = ''
    if obj.valid_ufn:
        validity = f'{obj.valid_from} - Until Further Notice'
    else:
        validity = f'{obj.valid_from} - {obj.valid_to}'

    applies_to_fuel = ''
    applies_to_service = ''

    if obj.applies_to_fuel:
        applies_to_fuel = 'Fuel'
        if obj.specific_fuel:
            applies_to_fuel = obj.specific_fuel
        elif obj.specific_fuel_cat:
            applies_to_fuel = obj.specific_fuel_cat

    if obj.applies_to_fees:
        applies_to_service = 'Services'
        if obj.specific_fee_category:
            applies_to_service = obj.specific_fee_category

    both = ''
    if obj.applies_to_fuel and obj.applies_to_fees:
        both = 'and'

    valid_for = ''
    if obj.applies_to_private and obj.applies_to_commercial:
        valid_for = f'Private, Commercial'
    elif obj.applies_to_private:
        valid_for = f'Private'
    elif obj.applies_to_commercial:
        valid_for = f'Commercial'

    if obj.pax_must_stay_aboard:
        pax = 'Pax Aboard: &#10003;'
    else:
        pax = 'Pax Aboard: &#10005;'

    if obj.waived_for_tech_stop:
        tech_stop = 'Tech Stop Exempt: &#10003;'
    else:
        tech_stop = 'Tech Stop Exempt: &#10005;'

    band_1 = ''
    band_2 = ''

    if obj.band_1_type:
        if obj.child_entries.all().exists():
            band_1 = f'{obj.band_1_type.name} ({normalize_fraction(obj.band_1_start)} - {normalize_fraction(obj.band_1_end)})\
                     - {obj.tax_rate_percentage.tax_percentage}%'
            for entry in obj.child_entries.all():
                band_1 += f' ({normalize_fraction(entry.band_1_start)} - {normalize_fraction(entry.band_1_end)})\
                          - {entry.tax_rate_percentage.tax_percentage}%'
        else:
            band_1 = f'{obj.band_1_type.name} ({normalize_fraction(obj.band_1_start)} - {normalize_fraction(obj.band_1_end)})\
                     - {obj.tax_rate_percentage.tax_percentage}%'

    if obj.band_2_type:
        if obj.child_entries.all().exists():
            band_2 = f'{obj.band_2_type.name} ({normalize_fraction(obj.band_2_start)} - {normalize_fraction(obj.band_2_end)})\
                     - {obj.tax_rate_percentage.tax_percentage}%'
            for entry in obj.child_entries.all():
                band_2 += f' ({normalize_fraction(entry.band_2_start)} - {normalize_fraction(entry.band_2_end)})\
                          - {entry.tax_rate_percentage.tax_percentage}%'
        else:
            band_2 = f'{obj.band_2_type.name} ({normalize_fraction(obj.band_2_start)} - {normalize_fraction(obj.band_2_end)})\
                     - {obj.tax_rate_percentage.tax_percentage}%'

    if obj.band_1_type or obj.band_2_type:
        rate = ''

    return f'{name} {region_or_airport} {rate} - {validity} |\
             {applies_to_fuel} {both} {applies_to_service} |\
             {valid_for} ({obj.applicable_flight_type.name} and {obj.geographic_flight_type.name}) |\
             {pax} {tech_stop} |\
             {band_1} {band_2}'


def taxruleexception_rule_from_instance(obj):
    '''
    Used to display 'Supplier-Defined Tax' (% based) for the taxable exception dropdown
    '''

    if obj is None:
        return ''

    if obj.tax.short_name:
        name = f'{obj.tax.local_name} ({obj.tax.short_name})'
    else:
        name = f'{obj.tax.local_name}'

    rate = f'- {obj.tax_percentage}'

    validity = obj.valid_from

    applies_to_fuel = ''
    applies_to_service = ''

    if obj.applies_to_fuel:
        applies_to_fuel = 'Fuel'
        if obj.specific_fuel:
            applies_to_fuel = obj.specific_fuel
        elif obj.specific_fuel_cat:
            applies_to_fuel = obj.specific_fuel_cat

    if obj.applies_to_fees:
        applies_to_service = 'Services'
        if obj.specific_fee_category:
            applies_to_service = obj.specific_fee_category

    both = ''
    if obj.applies_to_fuel and obj.applies_to_fees:
        both = 'and'

    valid_for = ''
    if obj.applies_to_private and obj.applies_to_commercial:
        valid_for = f'Private, Commercial'
    elif obj.applies_to_private:
        valid_for = f'Private'
    elif obj.applies_to_commercial:
        valid_for = f'Commercial'

    pax = 'Pax Aboard: &#10003;' if obj.pax_must_stay_aboard else 'Pax Aboard: &#10005;'

    tech_stop = 'Tech Stop Exempt: &#10003;' if obj.waived_for_tech_stop else 'Tech Stop Exempt: &#10005;'

    band_1 = ''
    band_2 = ''

    if obj.band_1_type:
        if obj.child_entries.all().exists():
            band_1 = f'{obj.band_1_type.name} ({normalize_fraction(obj.band_1_start)} - {normalize_fraction(obj.band_1_end)})\
                    - {obj.tax_percentage}%'
            for entry in obj.child_entries.all():
                band_1 += f' ({normalize_fraction(entry.band_1_start)} - {normalize_fraction(entry.band_1_end)})\
                        - {entry.tax_percentage}%'
        else:
            band_1 = f'{obj.band_1_type.name} ({normalize_fraction(obj.band_1_start)} - {normalize_fraction(obj.band_1_end)})\
                    - {obj.tax_percentage}%'

    if obj.band_2_type:
        if obj.child_entries.all().exists():
            band_2 = f'{obj.band_2_type.name} ({normalize_fraction(obj.band_2_start)} - {normalize_fraction(obj.band_2_end)})\
                    - {obj.tax_percentage}%'
            for entry in obj.child_entries.all():
                band_2 += f' ({normalize_fraction(entry.band_2_start)} - {normalize_fraction(entry.band_2_end)})\
                        - {entry.tax_percentage}%'
        else:
            band_2 = f'{obj.band_2_type.name} ({normalize_fraction(obj.band_2_start)} - {normalize_fraction(obj.band_2_end)})\
                    - {obj.tax_percentage}%'

    if obj.band_1_type or obj.band_2_type:
        rate = ''

    return f'{name} {rate} - {validity} |\
             {applies_to_fuel} {both} {applies_to_service} |\
             {valid_for} ({obj.applicable_flight_type.name} and {obj.geographic_flight_type.name}) |\
             {pax} {tech_stop} |\
             {band_1} {band_2}'


def crosscheck_with_existing_children(form, taxed_taxes, has_band_pricing, instances_of_band_1, instances_of_band_2,
                                      context, form_number, type_checked, form_context):
    '''
    Used to check if modifying an 'Official Tax' or 'Supplier-Defined Tax' would result in a mismatch with associated
    taxable taxes and taxable exceptions
    '''

    changed_taxes = []
    reassigned_taxes = []

    if not taxed_taxes.exists():
        return '', ''

    # If any changes for historical exceptions or taxes, we need to trigger duplication (historical pricing) or
    # reassignment for current entries
    # tax_percentage is from exceptions, band_pricing_amount can be found in both
    if form_context != 'Supersede':
        if any(['band_pricing_amount' in form.changed_data, 'tax_percentage_rate' in form.changed_data,
                'tax_unit_rate' in form.changed_data, 'tax_percentage' in form.changed_data]):
            if type_checked == 'historical':
                return taxed_taxes, taxed_taxes
            else:
                reassigned_taxes = list(taxed_taxes)

        # last three is from official taxes
        if any(['charging_method' in form.changed_data, 'application_method' in form.changed_data,
                'fuel_pricing_unit' in form.changed_data, 'tax_rule_charging_method' in form.changed_data,
                'tax_percentage_rate_application_method' in form.changed_data, 'tax_unit_rate_application_method' in form.changed_data]):
            if type_checked == 'historical':
                return taxed_taxes, taxed_taxes
            else:
                reassigned_taxes = taxed_taxes

    band_1_type = form.cleaned_data.get('band_1_type')
    band_2_type = form.cleaned_data.get('band_2_type')
    flight_type = form.cleaned_data.get('applicable_flight_type')
    geographic_flight_type = form.cleaned_data.get('geographic_flight_type')
    specific_fuel = form.cleaned_data.get('specific_fuel')
    specific_fuel_cat = form.cleaned_data.get('specific_fuel_cat')
    specific_fee_category = form.cleaned_data.get('specific_fee_category')
    applies_to_fees = form.cleaned_data.get('applies_to_fees')
    applies_to_fuel = form.cleaned_data.get('applies_to_fuel')
    applies_to_private = form.cleaned_data.get('applies_to_private')
    applies_to_commercial = form.cleaned_data.get('applies_to_commercial')
    valid_from = form.cleaned_data.get('valid_from')
    pax_stays = form.cleaned_data.get('pax_must_stay_aboard')
    tech_stop = form.cleaned_data.get('waived_for_tech_stop')
    specific_airport = form.cleaned_data.get('specific_airport')
    exception_airport = form.cleaned_data.get('exception_airport')

    replace_bands = False

    if context == 'official':
        if form.cleaned_data.get('valid_ufn'):
            valid_ufn = True
            valid_to = date(9999,12,31)
        else:
            valid_to = form.cleaned_data.get('valid_to')
            valid_ufn = False
    else:
        valid_to = date(9999,12,31)
        valid_ufn = True

    for entry in taxed_taxes:

        if specific_airport and context == 'official':
            if specific_airport != entry.specific_airport:
                if entry not in changed_taxes:
                    changed_taxes.append(entry)

        elif specific_airport and context == 'exception':
            if specific_airport != entry.exception_airport:
                if entry not in changed_taxes:
                    changed_taxes.append(entry)

        elif exception_airport:
            if exception_airport != entry.exception_airport:
                if entry not in changed_taxes:
                    changed_taxes.append(entry)

        if not (flight_type == entry.applicable_flight_type or flight_type.code == 'A'):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (geographic_flight_type == entry.geographic_flight_type or geographic_flight_type.code == 'ALL'):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (specific_fuel == entry.specific_fuel or specific_fuel is None):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (specific_fuel_cat == entry.specific_fuel_cat or specific_fuel_cat is None):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (specific_fee_category == entry.specific_fee_category or specific_fee_category is None):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        # See comment on line 264-267
        if not (applies_to_fuel == entry.applies_to_fuel or applies_to_fuel):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (applies_to_fees == entry.applies_to_fees or applies_to_fees):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (applies_to_private == entry.applies_to_private or applies_to_private):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (applies_to_commercial == entry.applies_to_commercial or applies_to_commercial):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (pax_stays == entry.pax_must_stay_aboard or pax_stays):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if not (tech_stop == entry.waived_for_tech_stop or tech_stop):
            if entry not in changed_taxes:
                changed_taxes.append(entry)

        if form_context != 'Supersede':
            if valid_from > entry.valid_from:
                if entry not in changed_taxes:
                    changed_taxes.append(entry)

            if context == 'official':
                if entry.valid_to is not None:
                    if valid_to <= entry.valid_to:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

                elif not (valid_ufn == entry.valid_ufn or entry.valid_ufn):
                    if entry not in changed_taxes:
                        changed_taxes.append(entry)
            else:
                if entry.valid_to and valid_to < entry.valid_to:
                    if entry not in changed_taxes:
                        changed_taxes.append(entry)

        if entry.band_1_type is not None or entry.band_2_type is not None:

            if band_1_type == entry.band_2_type and band_2_type == entry.band_1_type:
                band_1_type, band_2_type = band_2_type, band_1_type
                replace_bands = True

            if band_1_type != entry.band_1_type and band_1_type != entry.band_2_type:
                if band_1_type is None:
                    if band_1_type == entry.band_1_type:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                else:
                    if band_2_type != entry.band_1_type and band_2_type != entry.band_2_type:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                    else:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

            if band_2_type != entry.band_1_type and band_2_type != entry.band_2_type:
                if band_2_type is None:
                    if band_1_type != entry.band_1_type:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                    else:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                else:
                    if band_1_type != entry.band_1_type and band_1_type != entry.band_2_type:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                    else:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

            # With bands, we have to check if their start and end range match (e.g.: 1-999999)
            if has_band_pricing:
                child_entries = entry.child_entries.all().order_by('band_1_start', 'band_2_start')
                entry_band_1_start = entry.band_1_start
                entry_band_1_end = child_entries[len(child_entries)-1].band_1_end
                entry_band_2_start = entry.band_2_start
                entry_band_2_end = child_entries[len(child_entries)-1].band_2_end

                band_1_start = form.cleaned_data.get('band_1_start')
                if instances_of_band_1 == 1:
                    band_1_end = form.cleaned_data.get('band_1_end')
                else:
                    band_1_end = form.cleaned_data.get(f'band_1_end-additional-{form_number}-{instances_of_band_1 - 1}')

                band_2_start = form.cleaned_data.get('band_2_start')

                if instances_of_band_2 == 1:
                    band_2_end = form.cleaned_daat.get('band_2_end')
                else:
                    band_2_end = form.cleaned_data.get(f'band_2_end-additional-{form_number}-{instances_of_band_2 - 1}')

                if band_1_type:
                    if entry_band_1_start != band_1_start:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)
                    if entry_band_1_end > band_1_end:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

                if band_2_type:
                    if entry_band_2_start != band_2_start:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

                    if entry_band_2_end > band_2_end:
                        if entry not in changed_taxes:
                            changed_taxes.append(entry)

                # Check if the taxable tax is more "detailed" than the one we create (e.g.: it has 1-250 / 251-500 bands
                # while the one we create has a 1-500 band)
                if (instances_of_band_1 != child_entries.count() or instances_of_band_2 != child_entries.count()) and \
                    child_entries.count() != 0:
                    if context == 'exception':
                       all_taxed_entries = TaxRuleException.objects.filter(id = entry.id).union(child_entries)
                    else:
                       all_taxed_entries = TaxRule.objects.filter(id = entry.id).union(child_entries)

                    for field, value in list(form.cleaned_data.items()):
                        if 'band_1_start' in field:
                            if replace_bands:
                                band_2_start = value
                            else:
                                band_1_start = value
                            continue

                        if 'band_1_end' in field:
                            if replace_bands:
                                band_2_end = value
                            else:
                                band_1_end = value
                            continue

                        if 'band_2_start' in field:
                            if replace_bands:
                                band_1_start = value
                            else:
                                band_2_start = value
                            continue

                        if 'band_2_end' in field:
                            if replace_bands:
                                band_1_end = value
                            else:
                                band_2_end = value

                            if band_1_start is not None:
                                # Note: logic has changed here!
                                for taxed_entry in all_taxed_entries:
                                    if (band_1_end - band_1_start < taxed_entry.band_1_end - taxed_entry.band_1_start) and\
                                        band_1_end >= taxed_entry.band_1_end and band_1_start <= taxed_entry.band_1_start:

                                        if entry not in changed_taxes:
                                            changed_taxes.append(entry)
                                        break

                            if band_2_start is not None:
                                for taxed_entry in all_taxed_entries:
                                    if (band_2_end - band_2_start < taxed_entry.band_2_end - taxed_entry.band_2_start) and\
                                        band_2_end >= taxed_entry.band_2_end and band_2_start <= taxed_entry.band_2_start:

                                        if entry not in changed_taxes:
                                            changed_taxes.append(entry)
                                        break

        else:
            # No bands, for the taxed tax, but we have bands... (edited to have bands)
            if band_1_type is not None or band_2_type is not None:
                if entry.band_1_type is None or band_2_type is None:
                    changed_taxes.append(entry)


    if type_checked == 'historical':
        return changed_taxes, changed_taxes
    else:
        return reassigned_taxes, changed_taxes


def validate_band_rows(cleaned_data_copy, form, form_number, band_type, band_number_type):

        band_start_values = []
        band_end_values = []

        for field, value in cleaned_data_copy.items():

            if f'{band_type}_start' in field:
                if value is None:
                    form.add_error(field, '')
                else:
                    band_start_values.append(Decimal(value))

            elif f'{band_type}_end' in field:
                if value is None:
                    form.add_error(field, '')
                else:
                    band_end_values.append(Decimal(value))

        if len(band_start_values) == len(band_end_values): # else we have errors
            for num, entry in enumerate(band_start_values[1:len(band_start_values)]):
                if entry < band_end_values[num] or entry == band_end_values[num]:
                    if num == 0:
                        form.add_error(f'{band_type}_end', '')
                    else:
                        form.add_error(f'{band_type}_end-additional-{form_number}-{num}', '')
                    form.add_error(f'{band_type}_start-additional-{form_number}-{num+1}', '')

                    if 'Band Range mismatch detected' not in str(form.errors):
                        form.add_error(None, 'Band Range mismatch detected')

                decimal_places_end = find_decimals(band_end_values[num])
                decimal_places_start = find_decimals(entry)
                decimal_places = decimal_places_end if decimal_places_end > decimal_places_start else decimal_places_start
                absolute_tolerance = get_band_tolerance(decimal_places)

                if entry - band_end_values[num] != absolute_tolerance:
                    if num == 0:
                        form.add_error(f'{band_type}_end', '')
                    else:
                        form.add_error(f'{band_type}_end-additional-{form_number}-{num}', '')
                    form.add_error(f'{band_type}_start-additional-{form_number}-{num+1}', '')

                    if 'Bands should be present without gaps between them' not in str(form.errors):
                        form.add_error(None, 'Bands should be present without gaps between them')

            decimal_places = find_decimals(band_start_values[0])
            absolute_tolerance = get_band_tolerance(decimal_places)

            if band_start_values[0] != absolute_tolerance:
                form.add_error(f'{band_type}_start', '')
                if band_number_type == 'decimal':
                    message = 'The first band should have a starting value of 1, 0.1, 0.01, 0.001 or 0.0001'
                else:
                    message = 'The first band should have a starting value of 1'
                form.add_error(None, message)

            if band_end_values[-1] <= band_start_values[-1]:
                if len(band_end_values) == 0:
                    form.add_error(f'{band_type}_end', '')
                else:
                    form.add_error(f'{band_type}_start-additional-{form_number}-{len(band_end_values) - 1}', '')
                    form.add_error(f'{band_type}_end-additional-{form_number}-{len(band_end_values) - 1}', '')

                if 'Band Range mismatch detected' not in str(form.errors):
                    form.add_error(None, 'Band Range mismatch detected')
