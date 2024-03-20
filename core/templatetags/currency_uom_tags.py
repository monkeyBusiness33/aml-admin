from decimal import Decimal, ROUND_HALF_UP
from django import template


register = template.Library()
rounding = ROUND_HALF_UP


@register.simple_tag(name='custom_round_to_str')
def custom_round_to_str(amount, min_decimal_places, max_decimal_places, normalize_decimals=False):
    """
    Round to min_decimal_places (inc. trailing zeros), unless there are more significant digits,
    in which case round to max_decimal_places excluding trailing zeroes
    """
    decimal_pattern_min = f"0.{(min_decimal_places - 1) * '0'}1" if min_decimal_places > 0 else f"0"
    decimal_pattern_max = f"0.{(max_decimal_places - 1) * '0'}1"
    amount_rnd_2 = amount.quantize(Decimal(decimal_pattern_min), rounding)
    amount_rnd_max = amount.quantize(Decimal(decimal_pattern_max), rounding)

    if normalize_decimals:
        amount_rnd_max = amount_rnd_max.normalize()

    return f"""{amount_rnd_2 if amount == amount_rnd_2 else amount_rnd_max:,}"""


@register.simple_tag(name='as_currency')
def as_currency(amount, currency, use_div=False, min_decimal_places=2, max_decimal_places=4):
    if not amount:
        return '--'

    amount = Decimal(amount)

    if amount == Decimal(0):
        return '--'

    amount_str = custom_round_to_str(amount, min_decimal_places, max_decimal_places)

    return f"{amount_str} {currency['code']}{' ' + currency['division_name'] if use_div else ''}"


@register.simple_tag(name='price_unit_repr')
def price_unit_repr(rate, short=False):
    """
    Return a label including a calculation of price based on unit price and uplift in that unit
    e.g. 'per Cubic Metre × n Cubic Metres'
    """
    if rate['uom']['code'] == 'PU':
        # Fixed fees don't need unit calculation
        return rate['uom']['description']

    qty = Decimal(rate['converted_uplift_qty'] or 0)
    uom = rate['uom']

    qty_str = custom_round_to_str(qty, 4, 4)

    if short:
        return f"/{uom['code']} × {qty_str} {uom['code']}"

    if qty <= 1:
        return f"per {uom['description']} × {qty_str} {uom['description']}"
    else:
        return f"per {uom['description']} × {qty_str} {uom['description_plural']}"
