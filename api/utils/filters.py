import operator
from functools import reduce

import six
from django.db import models
from rest_framework import filters
from rest_framework.compat import distinct


class PrioritizedSearchFilter(filters.SearchFilter):
    search_param = "search"

    def filter_queryset(self, request, queryset, view):
        """Override to return prioritized results."""
        search_fields = getattr(view, 'search_fields', None)
        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        orm_lookups = [
            self.construct_search(six.text_type(search_field))
            for search_field in search_fields
        ]
        base = queryset

        # Will contain a queryset for each search term
        querysets = list()

        for search_term in search_terms:
            queries = [
                models.Q(**{orm_lookup: search_term})
                for orm_lookup in orm_lookups
            ]

            # Conditions for annotated priority value. Priority == inverse of the search field's index.
            # Example:
            #   search_fields = ['field_A', 'field_B', 'field_C']
            #   Priorities are field_A = 2, field_B = 1, field_C = 0
            when_conditions = [models.When(queries[i], then=models.Value(len(queries) - i - 1)) for i in
                               range(len(queries))]

            # Generate queryset result for this search term, with annotated priority
            querysets.append(
                queryset.filter(reduce(operator.or_, queries))
                .annotate(priority=models.Case(
                    *when_conditions,
                    output_field=models.IntegerField(),
                    default=models.Value(-1))  # Lowest possible priority
                )
            )

        queryset = reduce(operator.and_, querysets).order_by('-priority')

        if self.must_call_distinct(queryset, search_fields):
            # Filtering against a many-to-many field requires us to
            # call queryset.distinct() in order to avoid duplicate items
            # in the resulting queryset.
            # We try to avoid this if possible, for performance reasons.
            queryset = distinct(queryset, base)
        return queryset
