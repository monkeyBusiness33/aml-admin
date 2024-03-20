from rest_framework import generics, pagination
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from api.serializers.user import UserSettingsSerializer


class UserSettingsApiView(generics.RetrieveUpdateAPIView):
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser]
    serializer_class = UserSettingsSerializer

    def get_object(self):
        return self.request.user.settings
