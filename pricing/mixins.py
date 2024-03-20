from decimal import Decimal, ROUND_HALF_UP


class PricingCalculationMixin:
    '''
    This mixin collects some features universal to various forms of pricing (fees, taxes)
    used in calculation, to make results more uniform without implementing them multiple times.
    '''
    def __init__(self):
        self._unit_price = None
        self.issues = []
        self._notes = []
        self.currency_rates = {}

    @property
    def notes(self):
        if not self._notes and hasattr(self, 'apply_basic_notes'):
            self._notes = self.apply_basic_notes()

        return self._notes

    @property
    def unit_price(self):
        return self._unit_price

    @unit_price.setter
    def unit_price(self, value):
        '''
        Always round the unit price to 4 decimals (so that displayed value is the one used in calculations)
        '''
        if not isinstance(value, Decimal):
            value = Decimal(value)

        self._unit_price = value.quantize(Decimal('0.0001'), ROUND_HALF_UP)
