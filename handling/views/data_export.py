from handling.models import HandlingRequest
from handling.shared_views.data_export import HandlingRequestDataExportMixin
from user.mixins import AdminPermissionsMixin


class HandlingRequestDataExportView(AdminPermissionsMixin, HandlingRequestDataExportMixin):
    permission_required = ['handling.p_sfr_export_data']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.qs = HandlingRequest.objects.all()
