from fcm_django.models import FCMDevice
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework import status
from ..serializers.organisation import OrganisationWithLogoSerializer
from rest_framework.exceptions import PermissionDenied

from ..serializers.user import PersonSerializer


class ObtainAuthToken(ObtainAuthToken):
    """
    AML API Authentication view.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)

        if not serializer.errors:
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            app_mode = None
            app_perms = None
            user_position = None
            if user.is_superuser:
                app_mode = 'superuser'
            elif user.is_staff:
                app_mode = 'staff'
            else:
                user_position = user.person.primary_dod_position
                if user_position and user_position.applications_access.filter(
                        code__in=['dod_flightcrew', 'dod_planners', ],
                ).exists():
                    app_mode = 'military'
                    app_perms = user_position.applications_access.values_list('code', flat=True)
            
            if app_mode:
                data = {
                    'token': token.key,
                    'user_id': user.pk,
                    'email': user.username,
                    'username': user.username,
                    'title': user.person.details.title.name if user.person.details.title else None,
                    'fname': user.person.details.first_name,
                    'lname': user.person.details.last_name,
                    'person': PersonSerializer(user.person).data if hasattr(user, 'person') else None,
                    'organisation': OrganisationWithLogoSerializer(user_position.organisation).data if user_position else None,
                    'user_app_mode': app_mode,
                    'user_app_perms': app_perms,
                }
            else:
                raise PermissionDenied("You don't have permission to access")
            return Response({'data': data})


class FCMDeviceManagementView(FCMDeviceAuthorizedViewSet):
    '''
    Combined fcm.django's FCMDeviceAuthorizedViewSet view with
    the custom user's device deletion function.
    '''
    lookup_field = "registration_id"

    def destroy(self, request, *args, **kwargs):
        instance = FCMDevice.objects.filter(
            registration_id=self.request.query_params[self.lookup_field],
            user=self.request.user
        ).first()
        if instance:
            self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
