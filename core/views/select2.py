from django_select2.views import AutoResponseView

from user.mixins import AdminPermissionsMixin


class AuthenticatedSelect2View(AdminPermissionsMixin, AutoResponseView):
    permission_required = []
