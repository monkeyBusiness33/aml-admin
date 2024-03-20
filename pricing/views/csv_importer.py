from copy import deepcopy
from decimal import Decimal
from itertools import groupby

import sentry_sdk
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.forms import CharField, ChoiceField, ValidationError, widgets
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import FormView

from core.models import UnitOfMeasurement
from core.utils.uom import get_uom_conversion_rate
from organisation.form_widgets import AirportPickWidget
from pricing.fields import IpaOrganisationReconcileField
from pricing.forms import FuelPricingMarketCsvImporterForm
from pricing.form_widgets import IpaOrganisationReconcileWidget
from pricing.models import FuelPricingMarket, FuelPricingMarketIpaNameAlias
from pricing.utils.session import serialize_request_data
from user.mixins import AdminPermissionsMixin


class FuelPricingMarketCsvImporterView(AdminPermissionsMixin, FormView):
    form_class = FuelPricingMarketCsvImporterForm
    template_name = 'fuel_market_pricing_csv_importer.html'
    permission_required = ['pricing.p_create']

    IPA_NAME_SIMILARITY_THRESHOLD = 75

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors}, status=422)

    def form_valid(self, form):
        if form.needs_ipa_reconciliation:
            ipa_aliases = []
            ipa_form_rows = []

            for i, price in enumerate(form.needs_ipa_reconciliation):
                ipa_org_csv_name_field = self.get_ipa_org_csv_name_field(price.ipa_name)
                ipa_org_field = self.get_ipa_org_field(price.location, price.ipa_name_matches)

                form.fields.update({
                    f'ipa_org_csv_name_{i}': ipa_org_csv_name_field,
                    f'ipa_org_obj_{i}': ipa_org_field
                })

                ipa_value = ipa_org_field.widget.value_from_datadict(form.data, form.files, f'ipa_org_obj_{i}')

                try:
                    ipa_aliases.append((price.location, ipa_org_field.clean(ipa_value), price.ipa_name))
                except ValidationError as e:
                    form.add_error(f'ipa_org_obj_{i}', e)

                ipa_form_rows.append({
                    'ipa_org_csv_name_hidden': ipa_org_csv_name_field.widget.render(
                        f'ipa_org_csv_name_hidden_{i}', price.ipa_name),
                    'ipa_org_location': ChoiceField(
                        disabled=True,
                        choices=[(price.location, price.location.full_repr)],
                        widget=AirportPickWidget(attrs={
                            'class': 'form-control',
                            'disabled': 'disabled',
                        })).widget.render(f'ipa_org_location_{i}', price.location),
                    'ipa_org_csv_name_disp': CharField(
                        disabled=True,
                        widget=widgets.TextInput(attrs={
                            'class': 'form-control',
                            'disabled': 'disabled',
                        })).widget.render(f'ipa_org_csv_name_disp_{i}', price.ipa_name),
                    'ipa_org_obj': ipa_org_field.widget.render(f'ipa_org_obj_{i}', ipa_value or ipa_org_field.initial),
                    'ipa_org_obj_errors': form.errors.get(f'ipa_org_obj_{i}')
                })

            # On modal submission, save all the reconciled names
            if form.ipa_confirmed and not form.errors:
                ipa_alias_batch = []
                existing_aliases = FuelPricingMarketIpaNameAlias.objects.values_list('location', 'name', 'ipa')

                with transaction.atomic():
                    for location, ipa_pk, name in ipa_aliases:
                        if (int(location.pk), name, int(ipa_pk)) not in existing_aliases:
                            ipa_alias_batch.append(FuelPricingMarketIpaNameAlias(
                                location=location,
                                ipa_id=ipa_pk,
                                name=name.lower(),
                                created_by=self.request.user.person,
                            ))
                    FuelPricingMarketIpaNameAlias.objects.bulk_create(ipa_alias_batch, ignore_conflicts=True)
            else:
                return JsonResponse({
                    'ipa_form_html': render_to_string(
                        'fuel_pricing_import_ipa_reconciliation_form_body.html',
                        context={'form': form, 'ipa_form_rows': ipa_form_rows},
                        request=self.request
                    )
                })

        # Further validation of pricing match
        pld = form.cleaned_data.get('pld')
        new_pricing_data = form.clean_pricing_csv_file()

        try:
            pricing_updates = self.compare_pricing(pld, new_pricing_data)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

        # Also save settings for fees and taxes
        pricing_updates.update({
            'changes_to_fees': form.cleaned_data['changes_to_fees'],
            'changes_to_taxes': form.cleaned_data['changes_to_taxes']
        })

        # Store the results in session
        self.request.session[f'{pld.pk}-pricing_list_data_overrides'] = pricing_updates

        # Redirect to supersede page
        return JsonResponse({
            'redirect_url': reverse('admin:fuel_pricing_market_documents_supersede_pricing',
                                    kwargs={'pk': form.cleaned_data['pld'].pk})
        })

    @staticmethod
    def compare_pricing(pld, new_pricing_data):
        # We need to match each new pricing to some existing pricing exactly
        # (location + IPA + bands + applicability). Any mismatch should interrupt the process.
        # (It's okay if some existing pricing is not covered)

        # Since we've already reconciled locations and IPAs at this point, we just need
        # to group new rows by these and find existing pricing that matches
        # For this purpose, we make a pricing mapping in format (location, ipa): (old_pricing, new_pricing_rows)
        pricing_map = {}
        new_pricing = groupby(sorted(new_pricing_data, key=lambda x: (x.location.pk, x.ipa.pk if x.ipa else 0)),
                              lambda x: (x.location, x.ipa or None))

        old_pricing_list = sorted([p for loc in pld.pld_at_location.all() for p in filter(
            lambda x: x.price_active and not x.deleted_at, loc.fuel_pricing_market.all())],
                                  key=lambda x: (x.supplier_pld_location.location.pk, x.ipa.pk if x.ipa else 0))
        old_pricing = {k: list(v) for k, v in groupby(
            old_pricing_list, lambda x: (x.supplier_pld_location.location.pk, getattr(x.ipa, 'pk', None)))}

        missing_keys = []

        for key, new_pricing_set in new_pricing:
            old_pricing_key = key[0].pk, getattr(key[1], 'pk', None)
            if old_pricing_key not in old_pricing:
                missing_keys.append(key)
            else:
                pricing_map[key] = (old_pricing[old_pricing_key], list(new_pricing_set))

        if missing_keys:
            missing_keys_str = ''.join([f"<li><b>{key[0].airport_details.icao_code}:"
                                        f" {getattr(key[1], 'full_repr', 'TBC')}</b></li>"
                                        for key in missing_keys])

            raise ValidationError(f"Pricing for these Location-IPA pair(s) exists in the uploaded CSV"
                                  f" file, but not in the original pricing for this PLD: <ul>{missing_keys_str}</ul>"
                                  f"Please update the PLD to match the contents of the CSV file.")

        # Once we know that every location - ipa pair has a match, we check other criteria:
        # bands (with tolerance of +/- 10 USG), currency, uom, private/commercial and flight type
        pricing_update_map = {}
        usg_uom = UnitOfMeasurement.objects.filter(code='USG').first()

        for (location, ipa), (old_rows, new_rows) in pricing_map.items():
            # Check if row count matches
            if len(old_rows) != len(new_rows):
                raise ValidationError(f"New pricing for location-IPA pair <b>{location.airport_details.icao_code}:"
                                      f" {getattr(ipa, 'full_repr', 'TBC')}</b> consists of {len(new_rows)}"
                                      f" row{'' if len(new_rows) == 1 else 's'}, but the original pricing consists of"
                                      f" {len(old_rows)} row{'' if len(new_rows) == 1 else 's'}. Please update"
                                      f" the PLD to match the contents of the CSV file")

            # For each new row, try to match:
            # - an old row by band (+/- 10 USG) - convert exist. bands to USG (or assume default 99999(!) for no band)
            # - geographic type (DOM / INT / ALL)
            # - business type (private / commercial / both)
            for old_row in old_rows:
                if old_row.band_uom:
                    xr = get_uom_conversion_rate(old_row.band_uom, usg_uom, old_row.fuel)
                    old_row.band_start_usg = Decimal(old_row.band_start / xr)
                    old_row.band_end_usg = Decimal(min(old_row.band_end / xr, 99999))
                else:
                    old_row.band_start_usg = Decimal(0)
                    old_row.band_end_usg = Decimal(99999)

            for new_row in new_rows:
                old_row_matches = list(filter(lambda x: abs(x.band_start_usg - new_row.band_start_usg) <= 10
                                                        and abs(x.band_end_usg - new_row.band_end_usg) <= 10
                                                        and x.destination_type.code == new_row.destination_type
                                                        and x.applies_to_private == new_row.applies_to_private
                                                        and x.applies_to_commercial == new_row.applies_to_commercial,
                                              old_rows))

                # If there are still multiple matches, break ties using notes
                if len(old_row_matches) > 1:
                    for key, value in new_row.note_fields.items():
                        try:
                            field = FuelPricingMarket._meta.get_field(key)
                        except FieldDoesNotExist:
                            # Field that don't exist will be ignored, but should raise an issue for the dev team
                            sentry_sdk.capture_exception(ValidationError(
                                f"Field {key} does not exist on FuelPricingMarket"))
                            continue

                        if isinstance(field, models.ManyToManyField):
                            # For M2M, check if values include the matching field
                            old_row_matches = list(filter(
                                lambda x: value in getattr(x, key).values_list('pk', flat=True), old_row_matches))
                        else:
                            # For simple fields / FKs, just filter by value
                            old_row_matches = list(filter(lambda x: getattr(x, key) == value, old_row_matches))

                # At this point we've considered everything we know about so far,
                # so we can only proceed if there's exactly one match for the given row.
                if not old_row_matches:
                    raise ValidationError(
                        f"No matching band found for the following row (row {new_row.row_index}):<br><b>"
                        f"{location.airport_details.icao_code} - {getattr(ipa, 'full_repr', 'TBC')}"
                        f"</b> ({new_row.band_start_usg} - {new_row.band_end_usg} USG)")
                elif len(old_row_matches) > 1:
                    raise ValidationError(
                        f"More than one match was found for the following row (row {new_row.row_index}):<br><b>"
                        f"{location.airport_details.icao_code} - {getattr(ipa, 'full_repr', 'TBC')}"
                        f"</b> ({new_row.band_start_usg} - {new_row.band_end_usg} USG)")
                else:
                    old_row_match = old_row_matches[0]

                # If match found, check remaining criteria (currency & uom, private/commercial, geographic type)
                criteria_mismatch = {
                    'pricing_unit': new_row.pricing_unit != old_row_match.pricing_native_unit,
                    'destination_type': new_row.destination_type != old_row_match.destination_type.code,
                    'applies_to_commercial': new_row.applies_to_commercial != old_row_match.applies_to_commercial,
                    'applies_to_private': new_row.applies_to_private != old_row_match.applies_to_private,
                }

                if any(criteria_mismatch.values()):
                    raise ValidationError(
                        f"There is a mismatch in the following row (row {new_row.row_index}):<br><b>"
                        f"{location.airport_details.icao_code} - {getattr(ipa, 'full_repr', 'TBC')}"
                        f"</b> ({new_row.band_start_usg} - {new_row.band_end_usg} USG) for fields:"
                        f"<ul>{''.join(['<li>' + k + '</li>' for k, v in criteria_mismatch.items() if v])}</ul>."
                        f" Please update the PLD to match the contents of the CSV file")

                # Once all validation passed, map new prices and dates to existing pks
                pricing_update_map[old_row_match.pk] = {
                    'new_valid_from': new_row.valid_from_date.strftime('%Y-%m-%d'),
                    'new_valid_to': new_row.valid_to_date.strftime('%Y-%m-%d'),
                    'new_pricing_native_amount': new_row.price,
                }

        return pricing_update_map

    @staticmethod
    def get_ipa_org_csv_name_field(ipa_name):
        return CharField(
            required=True, disabled=True, initial=ipa_name,
            widget=widgets.HiddenInput()
        )

    def get_ipa_org_field(self, location, ipa_name_matches):
        choices = [(ipa.pk, self.get_ipa_repr(ipa, score)) for ipa, score in ipa_name_matches]
        use_initial = max([scr for _, scr in ipa_name_matches] + [0]) >= self.IPA_NAME_SIMILARITY_THRESHOLD
        initial = choices[0][0] if choices and use_initial else None
        return IpaOrganisationReconcileField(
            required=False, initial=initial, choices=choices,
            widget=IpaOrganisationReconcileWidget(
                attrs={
                    'class': 'form-control',
                    'required': 'required',
                },
                airport_location=location,
            ))

    @staticmethod
    def get_ipa_repr(ipa, score):
        return f'{ipa.full_repr} <span class="text-gray-400">({score}%)</span>'
