from django_select2 import forms as s2forms
from organisation.models.airport import AirportDetails
from organisation.models.handler import HandlerType
from organisation.models.operator import OperatorType
from organisation.models.organisation import OrganisationDetails, OrganisationType
from user.models import Person


class CrmActivityPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')
