from handling.form_widgets import OrganisationTailNumberDependedPickWidget


class MissionTailNumberDependedPickWidget(OrganisationTailNumberDependedPickWidget):
    dependent_fields = {
        'aircraft_type': 'aircraft__type',
        'aircraft_type_override': 'aircraft__type',
    }
