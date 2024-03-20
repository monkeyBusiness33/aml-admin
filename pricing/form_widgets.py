from django_select2 import forms as s2forms
from pricing.models.tax import Tax, TaxRule, TaxRuleException
from organisation.models import Organisation
from django.db.models import Q
from .utils.tax import taxrule_label_from_instance, taxruleexception_rule_from_instance
from .utils.fuel_pricing_market import normalize_fraction
from handling.form_widgets import represent_int, force_str
from organisation.models.organisation import Organisation, OrganisationDetails, OrganisationRestricted
from django.shortcuts import get_object_or_404
from organisation.models import IpaDetails, OrganisationDocument
from .models import FuelIndex, FuelIndexDetails
from core.models.pricing_unit import PricingUnit


class PricingUnitPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "unit_code__icontains",
        "description__icontains",
        "description_short__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.description} ({obj.unit_code})')


class FuelQuantityPricingUnitPickWidget(s2forms.ModelSelect2Widget):
    model = PricingUnit
    queryset = model.objects.filter(uom__is_fluid_uom=True)
    search_fields = [
        "unit_code__icontains",
        "description__icontains",
        "description_short__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.description} ({obj.unit_code})')


class FuelIndexPickWidget(s2forms.ModelSelect2Widget):
    model = FuelIndex
    queryset = model.objects.all()
    search_fields = [
        "name__icontains",
        "provider__details__registered_name__icontains",
        "provider__details__trading_name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select Fuel Pricing Index'
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj}')


class FuelIndexDetailsPickWidget(s2forms.ModelSelect2Widget):
    model = FuelIndexDetails
    search_fields = [
        "structure_str__icontains",
    ]

    def get_queryset(self):
        qs = super().get_queryset()

        return qs.with_status() \
            .order_by('-index_price_is_low', '-index_price_is_mean', '-index_price_is_high',
                      '-index_period_is_daily', '-index_period_is_weekly', '-index_period_is_fortnightly',
                      '-index_period_is_monthly')

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select Index Structure'
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.index_price_repr} / {obj.index_period_repr}')

    def optgroups(self, name, value, attrs=None):
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}

        query = Q(**{"%s__in" % 'pk': selected_choices})
        if value[0] != '':
            # This had to be added for the widget to work with externally provided querysets,
            # as self.queryset is None at this point if queryset is not provided at the top of the class,
            if self.queryset is None:
                self.queryset = self.get_queryset()

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



class IpaOrganisationPickCreateWidget(s2forms.ModelSelect2TagWidget):
    allow_multiple_selected = False
    queryset = Organisation.objects.all()
    search_fields = [
        "details__registered_name__icontains",
    ]

    def optgroups(self, name, value, attrs=None):
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
        super().__init__(*args, **kwargs)
        self.airport_location = kwargs.pop('airport_location', None)
        self.context = kwargs.pop('context', None)
        self.form_name = kwargs.pop('form_name', None)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-minimum-input-length": 0,
            "data-tags": "true",
            "data-token-separators": '[]',
            "data-placeholder": 'Select or Create an Into-Plane Agent'
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

                # Get Location
                if self.airport_location is not None:
                    request_location = self.airport_location
                elif self.context == 'formset':
                    request_location = get_object_or_404(Organisation, pk=data[f'{self.form_name}-location'])
                else:
                    request_location = get_object_or_404(Organisation, pk=data['location'])

                if not ipa_organisation_qs.exists():

                    request_country = None
                    if request_location.details.type_id == 8:
                        request_country = request_location.airport_details.region.country
                    elif request_location.details.type_id == 1002:
                        request_country = request_location.details.country

                    # Create OrganisationDetails record
                    organisation_details, created = OrganisationDetails.objects.update_or_create(
                        registered_name=val, type_id=4,
                        defaults={
                            'country': request_country,
                        },
                    )

                    organisation = Organisation.objects.create(details=organisation_details)

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    organisation.ipa_locations.set([request_location])
                    ipa_details, created = IpaDetails.objects.update_or_create(
                        organisation=organisation,
                    )
                    organisation_restricted, created = OrganisationRestricted.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'is_service_supplier': True,
                        },
                    )

                    val = organisation.pk
                else:
                    # Get IPA (presumably) organisation
                    ipa_organisation = ipa_organisation_qs.first()

                    # Generate QS to check IPA availability for the location
                    ipa_with_location = ipa_organisation_qs.filter(
                        ipa_locations=request_location)

                    # Append "IPA Location" ONLY for the IPA organisation
                    if not ipa_with_location.exists() and ipa_organisation.ipa_details:
                        ipa_organisation.ipa_locations.add(request_location)

                    # Get organisation object with valid location availability if it exists
                    selected_ipa = ipa_with_location.first()
                    # Return organisation pk or 0 to raise validation error
                    val = selected_ipa.pk if selected_ipa else 0
        return val

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}')


class TaxPickWidget(s2forms.ModelSelect2Widget):
    model = Tax
    queryset = Tax.objects.all()
    search_fields = [
        "local_name__icontains",
        "category__name__icontains"
    ]

    def filter_queryset(self, request, term, queryset, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset)

        if dependent_fields:
            selected_airport = dependent_fields.get('selected_airport', None)
            selected_country = dependent_fields.get('selected_country', None)
            try:
                related_country = Organisation.objects.get(id = selected_airport).details.country
            except:
                related_country = selected_country

            queryset = queryset.filter(applicable_country = related_country)
        return queryset

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def optgroups(self, name, value, attrs=None):
        # This is needed to display initial values
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

    def label_from_instance(self, obj):
        return str(f'{obj.local_name} - {obj.category}')

class TaxRulePickWidget(s2forms.ModelSelect2Widget):
    model = TaxRule
    search_fields = [
        "tax_rate_percentage__tax__local_name__icontains",
        "tax_rate_percentage__tax__category__name__icontains"
    ]

    def filter_queryset(self, request, term, queryset, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset)

        if dependent_fields:
            selected_airport = dependent_fields.get('selected_airport', None)
            related_country = Organisation.objects.get(id = selected_airport).details.country
            if selected_airport:
                airport_object = Organisation.objects.get(id = selected_airport)

            queryset = queryset.filter(Q(parent_entry = None),
                                       Q(tax_rate_percentage__tax__category__name = 'Value-Added Tax'),
                                       Q(tax_rate_percentage__tax_rate__name = 'Standard'),
                                       Q(deleted_at__isnull = True),
                                       Q(tax_rate_percentage__tax__applicable_country = related_country) |
                                       Q(tax_rate_percentage__tax__applicable_region = airport_object.airport_details.region),
                                       Q(specific_airport = airport_object) | Q(specific_airport__isnull = True))\
                                .order_by('band_1_start','band_2_start')

        return queryset

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def optgroups(self, name, value, attrs=None):
        # This is needed to display initial values
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

    def label_from_instance(self, obj):
        return taxrule_label_from_instance(obj)


class TaxRuleExceptionPickWidget(s2forms.ModelSelect2Widget):
    model = TaxRuleException
    search_fields = [
        "tax__local_name__icontains",
        "tax__category__name__icontains"
    ]

    def filter_queryset(self, request, term, queryset, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset)

        if dependent_fields:
            selected_airport = dependent_fields.get('exception_airport', None)

            queryset = queryset.filter(exception_airport = selected_airport, parent_entry = None, valid_ufn = True,
                                       deleted_at__isnull = True)\
                               .order_by('band_1_start','band_2_start')

        return queryset

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def optgroups(self, name, value, attrs=None):
        # This is needed to display initial values
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

    def label_from_instance(self, obj):
        return taxruleexception_rule_from_instance(obj)


class TaxCategoriesPickWidget(s2forms.Select2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            "data-placeholder": "Select Included Tax Categories",
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)


class ClientPickWidget(s2forms.ModelSelect2Widget):
    model = Organisation
    queryset = model.objects.filter(operator_details__isnull=False).order_by('details__registered_name')
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select Specific Client',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.trading_and_registered_name}')


class SupplierPickWidget(s2forms.ModelSelect2Widget):
    model = Organisation
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def get_queryset(self):
        qs = super().get_queryset()

        return qs.order_by('details__registered_name').distinct()

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select Specific Client',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.trading_and_registered_name}')


class SourceDocPickWidget(s2forms.ModelSelect2Widget):
    model = OrganisationDocument
    queryset = model.objects.order_by('name')
    dependent_fields = {'source_organisation': 'organisation'}
    search_fields = [
        "name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select Source Document',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class AmlGroupCompanyPickWidget(s2forms.ModelSelect2Widget):
    model = Organisation
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
        "details__country__name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-placeholder': 'Select AML Group Company',
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.trading_and_registered_name} <i>({obj.details.country.name})</i>')


class HandlerPickWidget(s2forms.ModelSelect2Widget):
    """
    Handling Agent Picker
    """
    search_fields = [
        "details__registered_name__icontains",
        "details__trading_name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            'data-placeholder': 'All Ground Handlers',
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def optgroups(self, name, value, attrs=None):
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

    def label_from_instance(self, obj):
        return str(f'{obj.details.registered_name}')


class ApronTypePickWidget(s2forms.ModelSelect2Widget):
    """
    Apron Type Picker
    """
    search_fields = [
        "name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        default_attrs = {
            'data-placeholder': 'All Aprons',
            'data-minimum-input-length': 0,
        }
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def optgroups(self, name, value, attrs=None):
        """Return only selected options and set QuerySet from `ModelChoicesIterator`."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value}

        query = Q(**{"%s__in" % 'pk': selected_choices})
        if value[0] != '':
            # This had to be added for the widget to work with externally provided querysets,
            # as self.queryset is None at this point if queryset is not provided
            if self.queryset is None:
                self.queryset = self.get_queryset()

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

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class FuelFeeCategoryPickWidget(s2forms.Select2Widget):
    """
    Adds a data attributes:
     - 'data-fixed-uom-only' which is needed to trigger filtering of fee application methods (units)
        for fees that can't be based on fluid units.
     - 'data-overwing-only' - to fix hookup method
    """
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if getattr(value, 'instance', None):
            inst = value.instance
            option['attrs'].update({
                'data-fixed-uom-only': inst.applies_for_no_fuel_uplift or inst.applies_for_defueling,
                'data-overwing-only': inst.applies_to_overwing_only,
            })

        return option


class FuelFeeUomPickWidget(s2forms.Select2Widget):
    """
    Adds a data attribute 'data-fixed-uom' which is needed to filter
    fee application methods (units) for fees that can't be based on fluid units.
    """
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if getattr(value, 'instance', None):
            inst = value.instance
            option['attrs'].update({
                'data-fixed-uom': not inst.uom.is_fluid_uom,
            })

        return option


class ChargeServicesPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]


class CurrentPldPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "pld_name__icontains",
        "supplier__details__registered_name__icontains"
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            'data-placeholder': 'Select PLD to supersede',
            "data-minimum-input-length": 0,
        }
        default_attrs.update(base_attrs)

        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)

    def label_from_instance(self, obj):
        return str(f'{obj.pld_name}<i class="ms-2 text-gray-400">({obj.supplier.details.registered_name})</i>')


class IpaOrganisationReconcileWidget(s2forms.Select2TagWidget):
    allow_multiple_selected = False

    def __init__(self, *args, **kwargs):
        self.airport_location = kwargs.pop('airport_location', None)
        super().__init__(*args, **kwargs)

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            'data-placeholder': 'Please Select or Create an IPA',
            'data-minimum-input-length': 0,
            'data-allow-clear': 'true',
            'data-token-separators': '[]'
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

                # Get Location
                if self.airport_location is not None:
                    request_location = self.airport_location
                elif self.context == 'formset':
                    request_location = get_object_or_404(Organisation, pk=data[f'{self.form_name}-location'])
                else:
                    request_location = get_object_or_404(Organisation, pk=data['location'])

                if not ipa_organisation_qs.exists():

                    request_country = None
                    if request_location.details.type_id == 8:
                        request_country = request_location.airport_details.region.country
                    elif request_location.details.type_id == 1002:
                        request_country = request_location.details.country

                    # Create OrganisationDetails record
                    organisation_details, created = OrganisationDetails.objects.update_or_create(
                        registered_name=val, type_id=4,
                        defaults={
                            'country': request_country,
                        },
                    )

                    organisation = Organisation.objects.create(details=organisation_details)

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    organisation.ipa_locations.set([request_location])
                    ipa_details, created = IpaDetails.objects.update_or_create(
                        organisation=organisation,
                    )
                    organisation_restricted, created = OrganisationRestricted.objects.update_or_create(
                        organisation=organisation,
                        defaults={
                            'is_service_supplier': True,
                        },
                    )

                    name = f'{val} <span class="text-gray-400">(NEW)</span>'
                    val = organisation.pk

                    # Add the new value to choices
                    self.choices.append((val, name))
                else:
                    # Get IPA (presumably) organisation
                    ipa_organisation = ipa_organisation_qs.first()

                    # Generate QS to check IPA availability for the location
                    ipa_with_location = ipa_organisation_qs.filter(
                        ipa_locations=request_location)

                    # Append "IPA Location" ONLY for the IPA organisation
                    if not ipa_with_location.exists() and ipa_organisation.ipa_details:
                        ipa_organisation.ipa_locations.add(request_location)

                    # Get organisation object with valid location availability if it exists
                    selected_ipa = ipa_with_location.first()
                    # Return organisation pk or 0 to raise validation error

                    name = f'{val} <span class="text-gray-400">(NEW)</span>'
                    val = selected_ipa.pk if selected_ipa else 0

                    # Add the new value to choices (if an org matched)
                    if val:
                        self.choices.append((val, name))
        return val
