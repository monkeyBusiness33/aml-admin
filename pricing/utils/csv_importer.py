from datetime import datetime
from decimal import Decimal

import sentry_sdk
from thefuzz import process

from django.forms import ValidationError


class CsvImporterFuelPricing(object):
    DATE_FORMATS = {
        '%Y-%m-%d': 'YYYY-MM-DD',
        '%Y.%m.%d': 'YYYY.MM.DD'
    }

    DESTINATION_TYPE_MAP = {
        'all': 'ALL',
        'domestic': 'DOM',
        'international': 'INT',
    }

    UOM_CODES_MAP = {
        'LTR': 'L'
    }

    def __init__(self, pld, row_index, row_data, *args):
        self.pld = pld
        self.row_index = row_index
        self.row_data = row_data
        self.ipa_name = None
        self.ipa_name_matches = None
        self._initialize(*args)

    def _initialize(self, pricing_units, ipa_aliases, note_map):
        """
        Initialize object based on raw CSV data, including basic validation of file formatting.
        """
        self.location = self.parse_location(self.row_data[1])
        self.ipa = self.parse_ipa(self.row_data[3], ipa_aliases)
        self.band_start_usg = Decimal(self.row_data[4])
        self.band_end_usg = Decimal(self.row_data[5])
        self.price = float(self.row_data[6])
        self.pricing_unit = self.parse_pricing_unit(self.row_data[7], self.row_data[8], pricing_units)
        self.applies_to_commercial = self.row_data[9].lower() in ['all', 'commercial']
        self.applies_to_private = self.row_data[9].lower() in ['all', 'private']
        self.destination_type = self.DESTINATION_TYPE_MAP[self.row_data[10].lower()]
        self.include_taxes = True if self.row_data[11] == 'Yes' else False
        self.valid_from_date = self.parse_date(self.row_data[13], 'Effective From')
        self.valid_to_date = self.parse_date(self.row_data[14], 'Effective To')
        self.note = self.row_data[12]
        self.note_fields = self.parse_note(self.note, note_map)

    def parse_date(self, date, date_name):
        if not date:
            raise ValidationError(f"The '{date_name}' date is missing in row {self.row_index}."
                                  "<br>Both valid from and to dates are required for fuel pricing.")

        for date_format in self.DATE_FORMATS.keys():
            try:
                return datetime.strptime(date, date_format)
            except ValueError:
                pass

        raise ValidationError(f"The '{date_name}' date: {date} could not be processed (row {self.row_index})."
                              f"<br>Acceptable formats are: {', '.join(self.DATE_FORMATS.values())}")

    def parse_ipa(self, ipa_name, ipa_aliases):
        try:
            if ipa_name.lower() == 'provided on order':
                return None
            else:
                location_ipas = set(self.location.ipas_here.all())
                location_ipa_name_list = [ipa.details.registered_name.lower() for ipa in location_ipas]
                ipa_name_matches = process.extract(ipa_name.lower(), location_ipa_name_list, limit=None)
                ipa_alias_matches = list(filter(lambda a: a.location == self.location and a.name == ipa_name.lower(),
                                                ipa_aliases))

                if ipa_name_matches and ipa_name_matches[0][1] == 100:
                    # If there's a 100% match, we can just use that IPA
                    return next(filter(lambda ipa: ipa.details.registered_name.lower() == ipa_name_matches[0][0],
                                       location_ipas))
                elif ipa_alias_matches:
                    ipa_alias = ipa_alias_matches[0]
                    return ipa_alias.ipa
                else:
                    # The user will have to reconcile new name manually
                    self.ipa_name = ipa_name
                    self.ipa_name_matches = [(next(filter(lambda ipa: ipa.details.registered_name.lower() == name[0],
                                                          location_ipas)), name[1]) for name in ipa_name_matches]
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise ValidationError(f"The IPA name <b>{ipa_name}</b> (row {self.row_index}) could not be reconciled."
                                  f"<br>ERROR: {e}.")

    def parse_location(self, icao_code):
        try:
            return next(filter(lambda loc: loc.airport_details.icao_code == icao_code, self.pld.locations.all()))
        except StopIteration:
            raise ValidationError(f"A location with icao code <b>{icao_code}</b> (row {self.row_index})"
                                  f" is not covered by the existing iteration of the PLD. Please update the PLD pricing"
                                  f" to match the contents of the CSV file. ")

    def parse_pricing_unit(self, currency_code, uom_code_raw, pricing_units):
        uom_code = self.UOM_CODES_MAP[uom_code_raw] if uom_code_raw in self.UOM_CODES_MAP else uom_code_raw

        try:
            # We use the code from the description instead of currency.code here
            # to account for possible usage of currency division codes (CADC, GBPP, USC etc.)
            return next(filter(
                lambda u: u.uom.code == uom_code and u.description_short.split(' ')[0] == currency_code, pricing_units))
        except StopIteration:
            raise ValidationError(f"A pricing unit could not be found based on uom code <b>{uom_code_raw}</b>"
                                  f" and currency code <b>{currency_code}</b> (row {self.row_index}).")

    def parse_note(self, note, note_map):
        # Parse the 'Notes' section, and for any string matches, set the relevant field value appropriately
        # This is later used for distinguishing otherwise identical rows if multiple matching rows found
        note_fields = {}

        if not note:
            return note_fields

        for note_field_match in note_map:
            if note_field_match.note_str.lower() in note.lower():
                note_fields.update({note_field_match.field_name: note_field_match.field_value})

        return note_fields
