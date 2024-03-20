from core.utils.datatables_functions import get_datatable_badge


def get_datatable_agreement_status_badge(fuel_agreement):
    if fuel_agreement.voided_at is not None:
        return get_datatable_badge(badge_text=f"{'Voided'}", badge_class=f"{'bg-gray-900'} datatable-badge-normal")
    else:
        return get_datatable_badge(badge_text=f"{'Published' if fuel_agreement.is_published else 'Unpublished'}",
                                   badge_class=f"{'bg-success' if fuel_agreement.is_published else 'bg-warning'}"
                                               f" datatable-badge-normal")
