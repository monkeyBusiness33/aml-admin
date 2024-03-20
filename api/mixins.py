from rest_framework.permissions import IsAuthenticated


class IsDoDPlannersUser(IsAuthenticated):

    def has_permission(self, request, view):
        person = getattr(request.user, 'person', None)
        if not person:
            return False
        
        user_position = person.primary_dod_position
        if not user_position:
            return False

        is_dod_planners_perm = user_position.applications_access.filter(
            code__in=['dod_planners', ],
        ).exists()

        return is_dod_planners_perm


class IsSuperUser(IsAuthenticated):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
