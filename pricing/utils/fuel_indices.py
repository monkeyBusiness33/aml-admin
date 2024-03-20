from core.templatetags.currency_uom_tags import custom_round_to_str


def fuel_index_pricing_check_overlap(index_pricing: dict, instance_pk: int, old_pricing_pk: int=None):
    """
    Check for overlap on index pricing addition/edition/supersede - prevent if a primary index
    pricing exists for a given fuel index and if overlap would occur after completing action
    """
    from pricing.models import FuelIndexPricing

    # Exclude the pricing instance itself, also on Supersede exclude the superseded pricing,
    # as its end date will be automatically adjusted to be the day before the start date of the new pricing.
    other_pricing = FuelIndexPricing.objects.filter(fuel_index_details=index_pricing['fuel_index_details']) \
        .exclude(pk__in=[instance_pk, old_pricing_pk])

    for other_price in other_pricing:
        if index_pricing['is_primary'] and other_price.is_primary \
            and (index_pricing.get('valid_to', None) is None or index_pricing['valid_to'] >= other_price.valid_from) \
            and (other_price.valid_to is None or other_price.valid_to >= index_pricing['valid_from']):
            msg = f"A primary price for this index and details with overlapping dates already exists:" \
                  f"<div class='text-center my-1'><b>" \
                  f" {custom_round_to_str(other_price.price, 2, 6, normalize_decimals=True)}" \
                  f" {other_price.pricing_unit.description}</b><br>" \
                  f" Valid: {other_price.valid_from} - {other_price.valid_to or 'UFN'}</div>"

            return msg
