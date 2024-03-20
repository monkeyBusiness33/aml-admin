import chardet
import csv
from io import TextIOWrapper

from django import forms
from django.core.validators import FileExtensionValidator
from django.forms import widgets

from core.models import PricingUnit
from pricing.form_widgets import CurrentPldPickWidget
from pricing.models import FuelPricingMarketCsvImporterNoteField, FuelPricingMarketIpaNameAlias, FuelPricingMarketPld
from pricing.utils.csv_importer import CsvImporterFuelPricing


class FuelPricingMarketCsvImporterForm(forms.Form):
    pld = forms.ModelChoiceField(
        queryset=FuelPricingMarketPld.objects.filter(is_current=True).order_by('pld_name'),
        label='PLD',
        widget=CurrentPldPickWidget(attrs={
            'class': 'form-control',
        }),
    )

    pricing_csv_file = forms.FileField(
        label='CSV File to Upload',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        widget=widgets.FileInput(attrs={
            'class': 'form-control',
        })
    )

    changes_to_fees = forms.ChoiceField(
        required=True,
        label='Any Changes To Fees',
        choices=[(1, 'Yes'), (0, 'No')],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input extend-label',
        }),
    )

    changes_to_taxes = forms.ChoiceField(
        required=True,
        label='Any Changes To Supplier-Defined Taxes',
        choices=[(1, 'Yes'), (0, 'No')],
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input extend-label',
        }),
    )

    needs_ipa_reconciliation = []
    csv_contents = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ipa_confirmed = kwargs.get('data', {}).get('ipa_confirmed')

    def clean_pld(self):
        return FuelPricingMarketPld.objects.filter(pk=self.cleaned_data['pld'].pk).prefetch_related(
            'locations__airport_details',
            'pld_at_location__fuel_pricing_market__ipa__details',
            'pld_at_location__location__ipas_here__details',
            'locations__details',
            'locations__ipas_here__details',
        ).first()

    def clean_changes_to_fees(self):
        return bool(int(self.cleaned_data['changes_to_fees']))

    def clean_changes_to_taxes(self):
        return bool(int(self.cleaned_data['changes_to_taxes']))

    def clean_pricing_csv_file(self):
        try:
            pld = self.cleaned_data['pld']

            pricing_units = PricingUnit.objects.all().prefetch_related('uom')
            ipa_aliases = FuelPricingMarketIpaNameAlias.objects.all()
            note_map = FuelPricingMarketCsvImporterNoteField.objects.all()

            if getattr(self, 'csv_contents', None):
                self.csv_contents = getattr(self, 'csv_contents')
            else:
                uploaded_file = self.cleaned_data['pricing_csv_file']

                # Check encoding (the files come from different computers and UTF-8 doesn't always work) and reset file
                encoding = chardet.detect(uploaded_file.read())['encoding']
                uploaded_file.seek(0)

                with TextIOWrapper(uploaded_file, encoding=encoding) as file:
                    csv_reader = csv.reader(file, delimiter=',')

                    # Skip header row
                    next(csv_reader)

                    self.csv_contents = [row for i, row in enumerate(csv_reader)]

            # Process remaining rows into objects
            new_pricing = [CsvImporterFuelPricing(pld, i + 2, row, pricing_units, ipa_aliases, note_map)
                           for i, row in enumerate(self.csv_contents)]

            # If processing was successful, check if any rows need IPA reconciliation
            self.needs_ipa_reconciliation = []
            needs_ipa_reconciliation = list(filter(lambda x: getattr(x, 'ipa_name_matches') is not None,
                                                   new_pricing))

            # Deduplicate the list of IPAs to reconcile
            used_locations_names = []

            for entry in needs_ipa_reconciliation:
                if (entry.location, entry.ipa_name) not in used_locations_names:
                    self.needs_ipa_reconciliation.append(entry)
                    used_locations_names.append((entry.location, entry.ipa_name))

        except forms.ValidationError as e:
            self.add_error(None, e)
            return

        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
            self.add_error(None, f'The file could not be parsed. Please check the formatting of the file.'
                                 f'<br>(EXCEPTION: {e})')
            return

        return new_pricing
