import re
from django.db.models import F, Q
from django_select2 import forms as s2forms
from aircraft.models import Aircraft


class AllAircraftRegistrationPickWidget(s2forms.ModelSelect2Widget):
    '''
    A widget to select any aircraft based on latest registration (removing punctuation
    to avoid misses due to differences in formatting) or type description.
    '''
    search_fields = [
        "type__manufacturer__icontains",
        "type__model__icontains",
        "type__designator__icontains",
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        term_wo_punctuation = re.sub(r'[^\w\d]', '', term)

        return super().filter_queryset(request, term, queryset, **dependent_fields).union(queryset.filter(
            registration_without_punctuation__icontains=term_wo_punctuation)
        )

    def label_from_instance(self, obj):
        return str(f'{obj.details} <i class="text-gray-500">- {obj.type}</i>')
