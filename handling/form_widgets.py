from django.db.models import Q
from django.utils.encoding import force_str
from django_select2 import forms as s2forms
from django_select2.cache import cache

from core.form_widgets import ModelSelect2WidgetWithPrioritizedFiltering
from handling.models import HandlingService, HandlingRequestDocumentType
from organisation.models import OperatorPreferredGroundHandler
from organisation.models.handler import HandlerDetails
from organisation.models.ipa import IpaDetails
from organisation.models.organisation import Organisation, OrganisationDetails, OrganisationRestricted
from user.models import Person


class OrganisationAircraftTypeDependedPickWidget(s2forms.ModelSelect2Widget):
    dependent_fields = {
        # 'customer_organisation': 'organisations', 'tail_number': 'aircraft_list__details'
        'customer_organisation': 'organisations',
        }
    search_fields = [
        "model__icontains",
        "designator__icontains",
    ]


class OrganisationTailNumberDependedPickWidget(s2forms.ModelSelect2Widget):
    dependent_fields = {
        'customer_organisation': 'operator',
        'aircraft_type': 'aircraft__type',
        }
    search_fields = [
        "registration__icontains",
    ]

    def __init__(self, *args, **kwargs):
        self.organisation = kwargs.get('organisation', None)
        super().__init__(*args, **kwargs)

    def set_to_cache(self):
        queryset = self.get_queryset()
        cache.set(
            self._get_cache_key(),
            {
                "organisation": self.organisation,
                "queryset": [queryset.none(), queryset.query],
                "cls": self.__class__,
                "search_fields": tuple(self.search_fields),
                "max_results": int(self.max_results),
                "url": str(self.get_url()),
                "dependent_fields": dict(self.dependent_fields),
            },
        )

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        if 'operator' in dependent_fields:
            organisation_id = dependent_fields.pop('operator')

            if organisation_id:
                self.organisation = Organisation.objects.get(pk=organisation_id)
                queryset = self.organisation.get_operable_fleet()

        qs = super().filter_queryset(request, term, queryset, **dependent_fields)
        return qs

    def label_from_instance(self, obj):
        return str(f'{obj.registration} <span class="ms-2 text-gray-400">{obj.operator.short_repr}</div>')


class HandlingRequestTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]


class HandlingRequestLocationPickWidget(ModelSelect2WidgetWithPrioritizedFiltering):
    order_results_by_search_fields = True
    search_fields = [
        "airport_details__icao_code__icontains",
        "airport_details__iata_code__icontains",
        "details__registered_name__icontains",
    ]

    def __init__(self, *args, **kwargs):
        kwargs['data_view'] = 'handling_locations_select2'
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return str(f'{obj.full_repr}')


class CrewMemberPositionPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


def represent_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


class HandlingServicePickCreateWidget(s2forms.ModelSelect2TagWidget):
    allow_multiple_selected = False
    queryset = HandlingService.objects.all()
    search_fields = [
        "name__icontains",
    ]

    def __init__(self, *args, **kwargs):
        request = kwargs.get('request')
        if request:
            if request.user.is_staff:
                kwargs['data_view'] = 'admin:handling_services_select2'
            else:
                kwargs['data_view'] = 'dod:handling_services_select2'
        super().__init__(*args, **kwargs)
        self.handling_request = kwargs.pop('handling_request', None)
        self.is_dla = kwargs.pop('is_dla', None)
        self.is_spf_visible = kwargs.pop('is_spf_visible', None)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 1,
            "data-tags": "true",
            "data-token-separators": '[]',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def value_from_datadict(self, data, files, name):
        # Get input value as list
        values = super().value_from_datadict(data, files, name)
        queryset = self.get_queryset()
        # Get database object pk if input value isdigits (ie. selected existing object)
        pks = queryset.filter(**{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(val) not in pks:
                if not queryset.filter(name=val).exists():
                    val = queryset.create(
                        name=val,
                        is_active=False,
                        is_dla=self.is_dla,
                        is_spf_visible=self.is_spf_visible,
                        custom_service_for_request=self.handling_request).pk
                else:
                    val = queryset.get(name=val).pk
        return val

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class FuelRequiredPickWidget(s2forms.Select2Widget):
    search_fields = [
        "code__icontains",
    ]


class IpaOrganisationPickCreateWidget(s2forms.ModelSelect2TagWidget):
    allow_multiple_selected = False
    queryset = Organisation.objects.all()
    search_fields = [
        "details__registered_name__icontains",
    ]

    def optgroups(self, name, value, attrs=None):
        from django.db.models import Q
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}

        query = Q(**{"%s__in" % 'pk': selected_choices})
        if value[0] != '':
            for obj in self.queryset.filter(query):
                option_value = obj.pk
                option_label = self.label_from_instance(obj)

                selected = str(option_value) in value and (
                        has_selected is False or self.allow_multiple_selected
                )
                if selected is True and has_selected is False:
                    has_selected = True
                index = len(default[1])
                subgroup = default[1]
                subgroup.append(
                    self.create_option(
                        name, option_value, option_label, selected_choices, index
                    )
                )
        return groups

    def __init__(self, *args, **kwargs):
        self.request = kwargs.get('request')

        if self.request and self.request.user.is_authenticated:
            if self.request.app_mode == 'ops_portal':
                kwargs['data_view'] = 'admin:select2'
            elif self.request.app_mode == 'dod_portal':
                kwargs['data_view'] = 'dod:select2'

        super().__init__(*args, **kwargs)
        self.handling_request = kwargs.pop('handling_request', None)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 0,
            "data-tags": "true",
            "data-token-separators": '[]',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def value_from_datadict(self, data, files, name):
        # Get input value as list
        values = super().value_from_datadict(data, files, name)
        queryset = Organisation.objects.filter(ipa_locations__isnull=False)
        # Get database object pk if input value isdigits (ie. selected existing object)
        pks = queryset.filter(
            **{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        val = None
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(val) not in pks and val != '':
                ipa_organisation_qs = queryset.filter(details__registered_name=val, ipa_locations__isnull=False)
                if not ipa_organisation_qs.exists():

                    # Get S&F Request Location country
                    request_location = self.handling_request.airport
                    request_country = None

                    if request_location.details.type_id == 8:
                        request_country = request_location.airport_details.region.country
                    elif request_location.details.type_id == 1002:
                        request_country = request_location.details.country

                    # Create OrganisationDetails record
                    organisation_details = OrganisationDetails.objects.create(
                        registered_name=val,
                        type_id=4,
                        country=request_country,
                        updated_by=self.request.user.person,
                    )

                    organisation = Organisation.objects.create(details=organisation_details)

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    organisation.ipa_locations.set([self.handling_request.airport])
                    ipa_details = IpaDetails.objects.create(
                        organisation=organisation,
                    )
                    organisation_restricted = OrganisationRestricted.objects.create(
                        organisation=organisation, is_service_supplier=True,
                    )

                    val = organisation.pk
                else:
                    # Get IPA (presumably) organisation
                    ipa_organisation = ipa_organisation_qs.first()

                    # Generate QS to check IPA availability for the location
                    ipa_with_location = ipa_organisation_qs.filter(
                        ipa_locations=self.handling_request.airport)

                    # Append "IPA Location" ONLY for the IPA organisation
                    if not ipa_with_location.exists() and ipa_organisation.ipa_details:
                        ipa_organisation.ipa_locations.add(self.handling_request.airport)

                    # Get organisation object with valid location availability if it exists
                    selected_ipa = ipa_with_location.first()
                    # Return organisation pk or 0 to raise validation error
                    val = selected_ipa.pk if selected_ipa else 0
        return val

    def label_from_instance(self, obj):
        return f'{obj.details.registered_name}' \
            + (f' <i class="text-gray-500">({obj.details.department_of.details.registered_name})</i>'
               if obj.details.department_of else '')


class HandlingAgentPickCreateWidget(s2forms.ModelSelect2TagWidget):
    """
    Handling Agent Pick or inline create field widget
    """
    allow_multiple_selected = False
    queryset = Organisation.objects.handling_agent()
    search_fields = [
        "details__registered_name__icontains",
    ]

    @property
    def empty_label(self):
        return self.empty_label_override

    def optgroups(self, name, value, attrs=None):
        from django.db.models import Q
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}

        query = Q(**{"%s__in" % 'pk': selected_choices})
        if value[0] != '':
            for obj in self.queryset.filter(query):
                option_value = obj.pk
                option_label = self.label_from_instance(obj)

                selected = str(option_value) in value and (
                    has_selected is False or self.allow_multiple_selected
                )
                if selected is True and has_selected is False:
                    has_selected = True
                index = len(default[1])
                subgroup = default[1]
                subgroup.append(
                    self.create_option(
                        name, option_value, option_label, selected_choices, index
                    )
                )
        return groups

    def __init__(self, *args, **kwargs):
        self.request = kwargs.get('request')
        if self.request:
            if self.request.app_mode == 'ops_portal':
                kwargs['data_view'] = 'admin:select2'
            elif self.request.app_mode == 'dod_portal':
                kwargs['data_view'] = 'dod:select2'

        super().__init__(*args, **kwargs)
        self.handling_request = kwargs.pop('handling_request', None)
        self.empty_label_override = kwargs.pop('empty_label', '')

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 0,
            "data-tags": "true",
            "data-token-separators": '[]',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def value_from_datadict(self, data, files, name):
        # Additional fields values
        contact_email = data.get('contact_email')
        contact_phone = data.get('contact_phone')
        ops_frequency = data.get('ops_frequency')

        # Get input value as list
        values = super().value_from_datadict(data, files, name)
        queryset = Organisation.objects.handling_agent()
        # Get database object pk if input value isdigits (ie. selected existing object)
        pks = queryset.filter(
            **{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        val = None
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(val) not in pks and val != '':
                if not queryset.filter(
                    details__registered_name=val,
                    handler_details__airport=self.handling_request.airport,
                ).exists():

                    organisation_details = OrganisationDetails.objects.create(
                        registered_name=val,
                        type_id=3,
                        country=self.handling_request.airport.airport_details.region.country,
                        updated_by=self.request.user.person,
                    )

                    organisation = Organisation.objects.create(
                        details=organisation_details)

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    handler_details, created = HandlerDetails.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'airport': self.handling_request.airport,
                            'handles_military': True,
                            'handler_type_id': 8,
                            'contact_email': contact_email,
                            'contact_phone': contact_phone or None,
                            'ops_frequency': ops_frequency or None,
                        },
                    )

                    organisation_restricted, created = OrganisationRestricted.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'is_service_supplier': True,
                        },
                    )

                    val = organisation.pk
                else:
                    selected_entity = queryset.filter(
                        details__registered_name=val,
                        handler_details__airport=self.handling_request.airport,
                    ).first()
                    val = selected_entity.pk if selected_entity else 0
        return val

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}')


class HandlingAgentWithBrandPickCreateWidget(HandlingAgentPickCreateWidget):
    def label_from_instance(self, obj):
        return f'{obj.details.registered_name}' \
            + (f' <i class="text-gray-500">({obj.details.department_of.details.registered_name})</i>'
               if obj.details.department_of else '')


class PreferredGroundHandlingPickWidget(s2forms.ModelSelect2TagWidget):
    dependent_fields = {
        'airport': 'handler_details__airport',
    }

    allow_multiple_selected = False
    queryset = Organisation.objects.handling_agent()
    search_fields = [
        "details__registered_name__icontains",
    ]

    @property
    def empty_label(self):
        return self.empty_label_override

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}')

    def optgroups(self, name, value, attrs=None):
        from django.db.models import Q
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}

        query = Q(**{"%s__in" % 'pk': selected_choices})
        if value[0] != '':
            for obj in self.queryset.filter(query):
                option_value = obj.pk
                option_label = self.label_from_instance(obj)

                selected = str(option_value) in value and (
                        has_selected is False or self.allow_multiple_selected
                )
                if selected is True and has_selected is False:
                    has_selected = True
                index = len(default[1])
                subgroup = default[1]
                subgroup.append(
                    self.create_option(
                        name, option_value, option_label, selected_choices, index
                    )
                )
        return groups

    def __init__(self, *args, **kwargs):
        self.request = kwargs.get('request')
        if self.request:
            if self.request.app_mode == 'ops_portal':
                kwargs['data_view'] = 'admin:select2'
            elif self.request.app_mode == 'dod_portal':
                kwargs['data_view'] = 'dod:select2'

        super().__init__(*args, **kwargs)
        self.handling_request = kwargs.pop('handling_request', None)
        self.empty_label_override = kwargs.pop('empty_label', '')

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 0,
            "data-tags": "true",
            "data-token-separators": '[]',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def value_from_datadict(self, data, files, name):
        # Additional fields values
        customer_organisation_id = data.get('customer_organisation')
        airport_id = data.get('airport')

        try:
            customer_organisation = Organisation.objects.get(pk=customer_organisation_id)
        except Organisation.DoesNotExist:
            dod_selected_position = getattr(self.request, 'dod_selected_position')
            customer_organisation = dod_selected_position.organisation

        airport = Organisation.objects.get(pk=airport_id)

        # Get input value as list
        values = super().value_from_datadict(data, files, name)
        queryset = Organisation.objects.handling_agent()
        # Get database object pk if input value is digits (ie. selected existing object)
        pks = queryset.filter(
            **{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        val = None
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(
                    val) not in pks and val != '':
                if not queryset.filter(
                        details__registered_name=val,
                        handler_details__airport=airport,
                ).exists():
                    organisation_details = OrganisationDetails.objects.create(
                        registered_name=val,
                        type_id=3,
                        country=airport.airport_details.region.country,
                        updated_by=self.request.user.person,
                    )

                    organisation = Organisation.objects.create(
                        details=organisation_details)

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    handler_details, created = HandlerDetails.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'airport': airport,
                            'handles_military': True,
                            'handler_type_id': 8,
                            'contact_email': None,
                        },
                    )

                    organisation_restricted, created = OrganisationRestricted.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'is_service_supplier': True,
                        },
                    )

                    val = organisation.pk
                else:
                    selected_entity = queryset.filter(
                        details__registered_name=val,
                        handler_details__airport=airport,
                    ).first()
                    val = selected_entity.pk if selected_entity else 0

        if val:
            preferred_handler_qs = OperatorPreferredGroundHandler.objects.filter(
                organisation=customer_organisation,
                location=airport,
            )
            if preferred_handler_qs.exists():
                preferred_handler_qs.update(ground_handler_id=val)
            else:
                OperatorPreferredGroundHandler.objects.create(
                    organisation=customer_organisation, location=airport, ground_handler_id=val,
                )

        return val


class PersonCrewDependentPickWidget(s2forms.ModelSelect2Widget):
    model = Person
    dependent_fields = {
        'person': 'sfr_crews',
    }

    search_fields = [
        "details__abbreviated_name__icontains",
        "details__contact_email__icontains",
        "details__first_name__icontains",
        "details__last_name__icontains",
    ]

    def filter_queryset(self, request, term, queryset, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset)
        select = Q()

        if dependent_fields:
            selected_person_ids = dependent_fields.get('sfr_crews__in', None)
            select &= ~Q(pk__in=selected_person_ids)

        queryset = queryset.filter(select)
        return queryset

    def label_from_instance(self, obj):
        return str(f'{obj.fullname}')


class HandlingRequestDocumentTypePickCreateWidget(s2forms.ModelSelect2TagWidget):
    allow_multiple_selected = False
    queryset = HandlingRequestDocumentType.objects.all()
    search_fields = [
        "name__icontains",
    ]

    def value_from_datadict(self, data, files, name):
        values = super().value_from_datadict(data, files, name)
        queryset = HandlingRequestDocumentType.objects.all()
        pks = queryset.filter(**{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        cleaned_value = None
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(val) not in pks:
                if not queryset.filter(name=val).exists():
                    val = queryset.create(name=val).pk
                else:
                    val = queryset.get(name=val).pk
            cleaned_value = val

        return cleaned_value


class HandlingServicePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class HandlingServicesPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class SfrOpsChecklistItemCategoryPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Checklist Item Category',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.name}')
