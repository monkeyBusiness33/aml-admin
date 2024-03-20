import re
from functools import reduce
import operator

from django.contrib.admin.utils import lookup_spawns_duplicates
from django.db.models import Q, Value, Case, When, IntegerField
from django_flatpickr.schemas import FlatpickrOptions
from django_select2 import forms as s2forms
from django.utils.encoding import force_str
from tagify.widgets import TagInput

from core.models import Tag

flatpickr_time_input_options = FlatpickrOptions(
    allow_input=True,
    altFormat='H:i'
)


class CountryPickWidget(s2forms.ModelSelect2Widget):
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


class CustomTagInput(TagInput):
    """
    A custom version of the Tagify multi-tag input, with an updated template, as the original
    template is outdated and the setting of minimum characters needed to show suggestion does not work.
    """
    template_name = "includes/custom_tagify_input.html"


class TagPickCreateWidget(s2forms.ModelSelect2TagWidget):
    queryset = Tag.objects.exclude(is_system=True).all()
    search_fields = [
        "name__icontains",
    ]

    def value_from_datadict(self, data, files, name):
        values = super().value_from_datadict(data, files, name)
        queryset = Tag.objects.all()
        pks = queryset.filter(**{'pk__in': [v for v in values if v.isdigit()]}).values_list('pk', flat=True)
        cleaned_values = []
        for val in values:
            if represent_int(val) and int(val) not in pks or not represent_int(val) and force_str(val) not in pks:
                if not queryset.filter(name=val).exists():
                    val = queryset.create(name=val).pk
                else:
                    val = queryset.get(name=val).pk
            cleaned_values.append(val)
        return cleaned_values


class AmlApplicationsPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class FuelCategoryPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class FuelTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name_with_nato_code}')


class FuelTypesPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name_with_nato_code}')


class UomPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "code__icontains",
        "description__icontains",
        "description_plural__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.description_plural} ({obj.code})')


class AirCardPrefixPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "number_prefix__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.number_prefix}')


class CurrencyPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'code__icontains',
        'name__icontains',
        'name_plural__icontains'
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name} ({obj.code})')


class FlightTypePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'name__icontains',
    ]

    def label_from_instance(self, obj):
        # Make the names more uniform
        label = re.sub('(.+Flight).*', r'\1', obj.name)

        return label


class ModelSelect2WidgetWithPrioritizedFiltering(s2forms.ModelSelect2Widget):
    order_results_by_search_fields = True

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        if queryset is None:
            queryset = self.get_queryset()
        search_fields = self.get_search_fields()
        select = Q()

        use_distinct = False
        if search_fields and term:
            for bit in term.split():
                or_queries = [Q(**{orm_lookup: bit}) for orm_lookup in search_fields]
                select &= reduce(operator.or_, or_queries)
            or_queries = [Q(**{orm_lookup: term}) for orm_lookup in search_fields]

            if self.order_results_by_search_fields:
                when_conditions = [When(or_queries[i], then=Value(len(or_queries) - i - 1)) for i in
                                   range(len(or_queries))]
                queryset = queryset.alias(s2_search_ordering_index=Case(
                    *when_conditions,
                    output_field=IntegerField(),
                    default=Value(-1))
                ).order_by('-s2_search_ordering_index')
            select |= reduce(operator.or_, or_queries)
            use_distinct |= any(
                lookup_spawns_duplicates(queryset.model._meta, search_spec)
                for search_spec in search_fields
            )

        if dependent_fields:
            select &= Q(**dependent_fields)

        use_distinct |= any(
            lookup_spawns_duplicates(queryset.model._meta, search_spec)
            for search_spec in dependent_fields.keys()
        )

        if use_distinct:
            return queryset.filter(select).distinct()
        return queryset.filter(select)


class HookupMethodPickWidget(s2forms.Select2Widget):
    search_fields = [
        'name__icontains',
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {
            "data-minimum-input-length": 0,
            'data-allow-clear': 'false',
        }
        default_attrs.update(base_attrs)

        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)
