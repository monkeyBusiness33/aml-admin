from django.http.response import JsonResponse
from django.views.generic.base import View

from user.mixins import AdminPermissionsMixin
from django.core.cache import cache
from redis.exceptions import ConnectionError, BusyLoadingError


class DummyJsonResponse(AdminPermissionsMixin, View):
    """
    Dummy json response that always return success:true
    Added due to async bootstrap-modal requires response to
    complete form submit.
    """
    permission_required = []

    def get(self, request, *args, **kwargs):
        resp = dict()
        resp['table'] = {'success': 'true'}
        return JsonResponse(resp)


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        is_error = False

        # Check redis connection
        try:
            cache.get(None)
            redis_connection = True
        except (ConnectionError, BusyLoadingError):
            redis_connection = False
            is_error = True

        # Check Postgresql connection
        from django.db.utils import ConnectionHandler, DatabaseError
        try:
            ConnectionHandler()['default'].ensure_connection()
            ConnectionHandler()['default_replica'].ensure_connection()
            postgres_connection_default = True
        except DatabaseError:
            postgres_connection_default = False
            is_error = True

        resp = {
            'r': redis_connection,
            'p': postgres_connection_default,
        }
        status_code = 503 if is_error else 200
        return JsonResponse(data=resp, status=status_code)
