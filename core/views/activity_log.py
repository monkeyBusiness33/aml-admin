from django.db.models import Q

from core.mixins import CustomAjaxDatatableView
from core.models import ActivityLog
from user.mixins import AdminPermissionsMixin


class ActivityLogAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = ActivityLog
    search_values_separator = '+'
    length_menu = [[25, 50, 100, 250, -1], [25, 50, 100, 250, 'all']]
    initial_order = [["created_at", "desc"], ]
    permission_required = []

    def has_permission(self):
        return any([
            self.request.user.has_perm('core.p_activity_log_view'),
            self.request.user.has_perm('handling.p_activity_log_view'),
        ])

    # QuerySet Optimizations
    prefetch_related = {
        'organisation',
        'person',
        'aircraft',
        'mission',
        'mission_leg',
        'mission_turnaround',
        'handling_request',
        'handling_request_movement',
    }

    def get_initial_queryset(self, request=None):
        entity_slug = self.kwargs['entity_slug']
        entity_pk = self.kwargs['entity_pk']
        entity_q = None

        if entity_slug == 'organisation':
            entity_q = Q(organisation_id=entity_pk)
        elif entity_slug == 'person':
            entity_q = Q(person_id=entity_pk)
        elif entity_slug == 'mission':
            entity_q = (Q(mission_id=entity_pk) | Q(mission_leg__mission_id=entity_pk) |
                        Q(mission_turnaround__mission_leg__mission_id=entity_pk))
        elif entity_slug == 'aircraft':
            entity_q = Q(aircraft_id=entity_pk)
        elif entity_slug == 'handling_request':
            entity_q = Q(handling_request_id=entity_pk) | Q(handling_request_movement__request_id=entity_pk)

        return self.model.objects.filter(entity_q) if entity_q else self.model.objects.none()

    column_defs = [
        {'name': 'pk', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'created_at', 'visible': True, 'width': '20px', 'searchable': False, },
        {'name': 'author', 'visible': True, 'foreign_field': 'author__details__first_name',
         'searchable': False, 'width': '30px', },
        {'name': 'details', 'title': 'Details', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['created_at'] = obj.get_created_at_display()
        row['author'] = obj.get_author_display()
        row['details'] = obj.get_details_display()
        return
