from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.http import Http404

# REST Framework imports
from rest_framework.response import Response
from rest_framework import exceptions
from rest_framework.exceptions import _get_error_details
from rest_framework.views import set_rollback
from rest_framework import status
from rest_framework.exceptions import ErrorDetail

# DRF JSON API imports
from rest_framework_json_api.exceptions import rendered_with_json_api
from rest_framework_json_api import utils
from rest_framework_json_api.settings import json_api_settings


def custom_drf_exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        is_json_api_view = rendered_with_json_api(context["view"])
        if is_json_api_view:
            data = {'errors': exc.detail}
            set_rollback()
            return Response(data, status=exc.status_code, headers=headers)

        if isinstance(exc.detail, ErrorDetail):
            data = {}
            data['errors'] = [{
                'detail': exc.detail,
                'code': exc.detail.code
            }]
            
        elif isinstance(exc.detail, dict):
                data = {}
                
                for item in exc.detail.items():
                    details = []
                    for detail in item[1]:
                        details.append({
                            'detail': detail,
                            'code': detail.code if 'code' in detail else None,
                        })
                    data[item[0]] = details

                # Custom exception response
                data = {'errors': data}
        else:
            data = {'errors': exc.detail}

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    return None


def json_api_exception_handler(exc, context):

    # Render exception with DRF
    response = custom_drf_exception_handler(exc, context)
    if not response:
        return response

    # Use regular DRF format if not rendered by DRF JSON API and not uniform
    is_json_api_view = rendered_with_json_api(context["view"])
    is_uniform = json_api_settings.UNIFORM_EXCEPTIONS
    if not is_json_api_view and not is_uniform:
        return response

    # Convert to DRF JSON API error format
    response = utils.format_drf_errors(response, context, exc)

    # Add top-level 'errors' object when not rendered by DRF JSON API
    if not is_json_api_view:
        response.data = utils.format_errors(response.data)

    return response

