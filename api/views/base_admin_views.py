from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.renderers import JSONRenderer

from aircraft.models import Aircraft, AircraftType
from api.serializers.aircraft import AircraftSerializer, AircraftTypeSerializer
from api.serializers.organisation import OrganisationSerializer
from organisation.models import Organisation


class IPAListView(generics.ListAPIView):
    """View returns non-paginated list of all IPA's"""

    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = OrganisationSerializer
    queryset = Organisation.objects.ipa().all()
    pagination_class = None


class OrganisationFleetView(generics.ListAPIView):
    """View returns non-paginated list of Organisation fleet"""

    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AircraftSerializer
    pagination_class = None

    def get_queryset(self):
        organisation = get_object_or_404(Organisation, pk=self.kwargs['pk'])
        fleet = organisation.get_operable_fleet().values_list('aircraft_id', flat=True)

        qs = Aircraft.objects.filter(
            id__in=fleet,
        ).select_related().prefetch_related(
            'type',
            'details__operator',
            'details__homebase',
            'details__homebase__details',
            'details__homebase__airport_details',
        )
        return qs


class OrganisationAircraftTypesView(generics.ListAPIView):
    """View returns non-paginated list of Organisation Aircraft Types"""

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AircraftTypeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = AircraftType.objects.filter(organisations=self.kwargs['pk'])
        return qs
