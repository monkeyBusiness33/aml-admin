

class DodPersonMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        person = getattr(request.user, 'person', None)
        if person:
            dod_selected_position_id = request.session.get('dod_selected_position', None)
            selected_position_qs = None

            # Pick position by id, when given
            if dod_selected_position_id:
                selected_position_qs = person.organisation_people.filter(
                    pk=dod_selected_position_id,
                    applications_access__code__in=['dod_flightcrew', 'dod_planners'],
                )

            # Pick first position
            if not selected_position_qs or not dod_selected_position_id:
                selected_position_qs = person.organisation_people.filter(
                    applications_access__code__in=['dod_flightcrew', 'dod_planners', ],
                )

            # Optimize QuerySet and fetch position
            selected_position = selected_position_qs.select_related().first()

            # Set request object values
            request.dod_selected_position = selected_position
            request.dod_selected_position_perms = selected_position.applications_access.values_list(
                'code', flat=True).cache()

            # Overwrite of the default 'ops_portal' variable from the "app.middlewares.OpsPortalMiddleware"
            request.app_mode = 'dod_portal'

        response = self.get_response(request)
        return response
