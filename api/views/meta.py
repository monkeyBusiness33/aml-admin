from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from api.serializers.organisation import OrganisationSerializer
from core.models import GlobalConfiguration


class MetaInformationApiView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request, *args, **kwargs):
        global_config = GlobalConfiguration.get_solo()
        response_dict = dict()

        if request.user.is_dod_portal_user:
            response_dict['dod_cs_ts'] = global_config.dod_cs_ts
            position = request.user.person.primary_dod_position
            if position:
                response_dict['organisation'] = OrganisationSerializer(position.organisation).data

        return Response(response_dict)
