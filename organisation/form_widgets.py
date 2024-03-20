from django_select2 import forms as s2forms
from core.utils.datatables_functions import get_datatable_badge
from organisation.models.airport import AirportDetails
from organisation.models.handler import HandlerType
from organisation.models.operator import OperatorType
from organisation.models.organisation import Organisation, OrganisationDetails, OrganisationType
from user.models import Person


class OrganisationPickWidget(s2forms.ModelSelect2Widget):
    model = OrganisationDetails
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}' + (f' T/A {obj.details.trading_name}' if obj.details.trading_name else ''))


class OrganisationWithTypePickWidget(s2forms.ModelSelect2Widget):
    model = OrganisationDetails
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def label_from_instance(self, obj):
        return f'{obj.details.registered_name}' \
            + (f' T/A {obj.details.trading_name}' if obj.details.trading_name else '') \
            + f'<i class="text-gray-500"> ({obj.details.type.name})</i>'


class OrganisationsPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "details__registered_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}')


class OperatorTypePickWidget(s2forms.ModelSelect2Widget):
    model = OperatorType
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class HandlerTypePickWidget(s2forms.ModelSelect2Widget):
    model = HandlerType
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class OrganisationPersonPickWidget(s2forms.ModelSelect2MultipleWidget):
    allow_multiple_selected = False
    dependent_fields = {'customer_organisation': 'organisations'}
    model = Person
    search_fields = [
        "details__abbreviated_name__icontains",
        "details__contact_email__icontains",
        "details__first_name__icontains",
        "details__last_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.fullname}')


class AirportPickWidget(s2forms.ModelSelect2Widget):
    model = AirportDetails
    search_fields = [
        "airport_details__icao_code__icontains",
        "airport_details__iata_code__icontains",
        "details__registered_name__icontains",
    ]

    def label_from_instance(self, obj):
        if self.attrs.get('icao_iata_label', False):
            return str(f'{obj.airport_details.icao_iata}')
        else:
            return str(f'{obj.airport_details.fullname}')


class AirportsPickWidget(s2forms.ModelSelect2MultipleWidget):
    model = AirportDetails
    search_fields = [
        "airport_details__icao_code__icontains",
        "airport_details__iata_code__icontains",
        "details__registered_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.airport_details.fullname}')


class OrganisationDocumentTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        org_type_suffix = f' - {obj.organisation_type.name}' if obj.organisation_type else ''

        return str(f'{obj.name}<span class="text-gray-400">{org_type_suffix}</div>')


class OrganisationPersonRolePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class NasdTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "description__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.description}')


class GroundServicesPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class ServiceProviderLocationPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "airport_details__icao_code__icontains",
        "airport_details__iata_code__icontains",
        "details__registered_name__icontains",
    ]

    def label_from_instance(self, obj):
        if hasattr(obj, 'airport_details'):
            return str(f'{obj.airport_details.fullname}')
        else:
            return str(f'{obj.details.registered_name}')


class OrganisationAircraftTypesPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "manufacturer__icontains",
        "model__icontains",
        "designator__icontains",
    ]


class OrganisationTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class OrganisationTypesPickWidget(s2forms.Select2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class OrganisationPersonPositionPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "person__details__first_name__icontains",
        "person__details__last_name__icontains",
        "organisation__details__registered_name__icontains",
        "organisation__airport_details__icao_code__icontains",
        "organisation__airport_details__iata_code__icontains",
    ]

    def label_from_instance(self, obj):
        return f'{obj.person.fullname}' \
            + f'<i class="text-gray-500"> ({obj.organisation.full_repr})</i>'


class OrganisationPeoplePickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "person__details__first_name__icontains",
        "person__details__last_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.person.fullname}')


class OrganisationRolePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "person__details__first_name__icontains",
        "person__details__last_name__icontains",
        "job_title__icontains",
    ]

    def label_from_instance(self, obj):
        return f'{obj.person.fullname} <i class="text-gray-500">({obj.job_title})</i>'


class OperatorAuthorisedPeoplePickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "person__details__first_name__icontains",
        "person__details__last_name__icontains",
        "person__details__title__name__icontains",
        "job_title__icontains",
    ]

    def label_from_instance(self, obj):
        return f'{obj.person.full_repr} ({obj.job_title})'


class OperatorPreferredHandlerDependentPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    dependent_fields = {
        'location': 'handler_details__airport',
    }

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}' + (f' T/A {obj.details.trading_name}' if obj.details.trading_name else ''))


class FuelIndexProviderPickWidget(s2forms.ModelSelect2Widget):
    model = OrganisationDetails
    queryset = Organisation.objects.filter(
        details__type__name="Fuel Index Provider")
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}' + (f' T/A {obj.details.trading_name}' if obj.details.trading_name else ''))


class AirportPickWidget2(s2forms.ModelSelect2Widget):
    '''
    I'm not sure about the working of the other AirportPickWidget,
    and this is needed only temporarily, until the calculation
    is placed on airport details page.
    '''
    search_fields = [
        "icao_code__icontains",
        "iata_code__icontains",
        "organisation__details__registered_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.fullname}')


class DlaServicePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]


class EmailFunctionPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return f'{obj.name}'


class OrganisationEmailControlAddressPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "label__icontains",
    ]

    def label_from_instance(self, obj):
        suffix_text = ''
        if obj.email_address:
            suffix_text = ', '.join(obj.get_email_address())
        elif obj.organisation:
            suffix_text = obj.organisation.trading_and_registered_name
        elif obj.organisation_person:
            suffix_text = '{person_fullname} - {organisation}'.format(
                person_fullname=obj.organisation_person.person.fullname,
                organisation=obj.organisation_person.organisation.full_repr,
            )

        label_text = f'{obj.label} - <i class="text-gray-500">({suffix_text})</i>'
        return label_text
