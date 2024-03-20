from dod_portal.mixins import DodPermissionsMixin
from handling.shared_views.data_export import HandlingRequestDataExportMixin


class HandlingRequestDataExportView(DodPermissionsMixin, HandlingRequestDataExportMixin):
    position = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.position = getattr(self.request, 'dod_selected_position')
        self.qs = self.position.organisation.handling_requests

    def has_permission(self):
        return self.position.role.is_ops
