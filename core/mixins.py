from ajax_datatable import AjaxDatatableView
from django.db.models import Prefetch
from django.conf import settings
from django.db import connections, reset_queries


class CustomAjaxDatatableView(AjaxDatatableView):
    """
    Modified AjaxDatatableView with possibility to optimize QuerySet
    Added SQL queries measurement for GET request method
    """
    select_related = None
    prefetch_related = None
    disable_queryset_optimization_only = True

    def optimize_queryset(self, qs):

        # use sets to remove duplicates
        only = set()
        select_related = self.select_related if self.select_related else set()
        prefetch_related = self.prefetch_related if self.prefetch_related else set()

        # collect values for qs optimizations
        fields = {f.name: f for f in self.model._meta.get_fields()}
        for column in self.column_specs:
            foreign_field = column.get('foreign_field')
            m2m_foreign_field = column.get('m2m_foreign_field')
            if foreign_field:
                only.add(foreign_field)
                select_related.add('__'.join(foreign_field.split('__')[0:-1]))
            elif m2m_foreign_field:
                split_field = m2m_foreign_field.split('__')
                if len(split_field) != 2:
                    raise Exception('m2m_foreign_field should be 2 level max ex : authors__name')
                m2m_field, m2m_name = split_field
                model = fields[m2m_field].related_model

                prefetch_related.add(Prefetch(m2m_field,
                                              queryset=model.objects.only(m2m_name).order_by(m2m_name),
                                              to_attr=f'{m2m_field}_list',
                                              ))
            else:
                [f.name for f in self.model._meta.get_fields()]
                field = column.get('name')
                if field in fields:
                    only.add(field)

        # convert to lists
        only = [item for item in list(only) if item]
        select_related = list(select_related)

        # apply optimizations:

        # (1) use select_related() to reduce the number of queries
        if select_related and not self.disable_queryset_optimization_select_related:
            qs = qs.select_related(*select_related)
        # (2) use prefetch_related() to optimize the numbers of queries
        if prefetch_related and not self.disable_queryset_optimization_prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)

        # (3) use only() to reduce the number of columns in the result set
        if only and not self.disable_queryset_optimization_only:
            qs = qs.only(*only)

        return qs

    def get(self, request, *args, **kwargs):

        if settings.DEBUG:
            reset_queries()

        response = super().get(request, *args, **kwargs)

        if settings.DEBUG:
            def query_count_all() -> int:
                query_total = 0
                for c in connections.all():
                    query_total += len(c.queries)
                return query_total

            print(f'<<<< QUERIES {self.__class__.__name__} >>>>', query_count_all())
            reset_queries()

        return response
