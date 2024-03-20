from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from api.serializers.organisation import OrganisationSerializer
from api.utils.filters import PrioritizedSearchFilter
from organisation.models import Organisation, OrganisationType


class OrganisationsFilter(filters.FilterSet):
    type = filters.ModelMultipleChoiceFilter(
        field_name='details__type_id',
        queryset=OrganisationType.objects.all(),
    )


class OrganisationsViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    renderer_classes = [JSONRenderer]
    serializer_class = OrganisationSerializer
    queryset = Organisation.objects.all()
    filter_backends = [DjangoFilterBackend, PrioritizedSearchFilter]
    filterset_class = OrganisationsFilter

    search_fields = [
        'airport_details__icao_code',
        'airport_details__iata_code',
        'details__registered_name',
        'details__trading_name',
    ]
