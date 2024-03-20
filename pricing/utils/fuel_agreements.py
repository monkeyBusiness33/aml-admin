from django.db.models import Q
from django.urls import reverse_lazy


def agreement_extension_check_overlap(fuel_agreement: 'FuelAgreement', extension_date):
    """
    Check for overlap on extension - prevent extension if the agreement covers supplier+location+IPA
    that is already covered by another agreement and where overlap would occur after extending
    """
    from pricing.models import FuelAgreement

    supplier_agreements = FuelAgreement.objects \
        .filter(Q(supplier=fuel_agreement.supplier) & ~Q(pk=fuel_agreement.pk)) \
        .prefetch_related('pricing_formulae', 'pricing_manual')

    for other_agreement in supplier_agreements:
        other_pricing_set = other_agreement.all_pricing

        for pricing in fuel_agreement.all_pricing:
            for other_pricing in other_pricing_set:
                if pricing.location == other_pricing.location and pricing.ipa == other_pricing.ipa \
                    and (extension_date is None or extension_date >= other_agreement.start_date) \
                    and (other_agreement.valid_ufn or other_agreement.end_date.date() >= fuel_agreement.start_date):
                    overlap_ag_url = reverse_lazy('admin:fuel_agreement', kwargs={'pk': other_agreement.pk})
                    msg = f"An agreement with <b>{fuel_agreement.supplier.full_repr}</b> at" \
                          f" <b>{other_pricing.location.full_repr}</b> with " \
                          f"{'<b>' + other_pricing.ipa.full_repr + '</b> acting as IPA' if other_pricing.ipa else 'no IPA'}" \
                          f" already exists:<div class='text-center my-1'>" \
                          f"<a href='{overlap_ag_url}'>{other_agreement}, {other_agreement.start_date}" \
                          f" - {other_agreement.end_date.date() if other_agreement.end_date else 'UFN'}</a></div>" \
                          f" and this action would result in an overlap." \
                          f" Please adjust the date accordingly."

                    return msg


def pricing_check_overlap(location, ipa, agreement, other_agreements):
    """
    Check for overlap on pricing addittion/edition - prevent if pricing covers supplier+location+IPA
    that is already covered by another agreement and where overlap would occur after extending
    """
    for other_agreement in other_agreements:
        other_pricing_set = other_agreement.all_pricing

        for other_pricing in other_pricing_set:
            if location == other_pricing.location and ipa == other_pricing.ipa \
                and (agreement.valid_ufn or agreement.end_date.date() >= other_agreement.start_date) \
                and (other_agreement.valid_ufn or other_agreement.end_date.date() >= agreement.start_date):
                overlap_ag_url = reverse_lazy('admin:fuel_agreement', kwargs={'pk': other_agreement.pk})
                msg = f"An agreement with <b>{agreement.supplier.full_repr}</b> at" \
                      f" <b>{other_pricing.location.full_repr}</b> with " \
                      f"{'<b>' + other_pricing.ipa.full_repr + '</b> acting as IPA' if other_pricing.ipa else 'no IPA'}" \
                      f" already exists:<div class='text-center my-1'>" \
                      f"<a href='{overlap_ag_url}'>{other_agreement}, {other_agreement.start_date}" \
                      f" - {other_agreement.end_date.date() if other_agreement.end_date else 'UFN'}</a></div>" \
                      f" and this action would result in an overlap." \
                      f" Please adjust the date accordingly."

                return msg
