from rest_framework import generics
from rest_framework.renderers import JSONRenderer

from aircraft.models import Aircraft
from api.serializers.aircraft import AircraftSerializer
from api.serializers.organisation import OrganisationPeopleSerializer


class OrganisationFleetView(generics.ListAPIView):
    """
    Returns un paginated list of Organisation fleet
    """
    serializer_class = AircraftSerializer
    pagination_class = None
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        position = self.request.user.person.primary_dod_position
        if not position:
            return []
        fleet = position.organisation.get_operable_fleet().values_list('aircraft_id', flat=True)
        qs = Aircraft.objects.filter(
            id__in=fleet,
            type__in=position.aircraft_types.all(),
        ).select_related().prefetch_related(
            'type',
            'details__operator',
            'details__homebase',
            'details__homebase__details',
            'details__homebase__airport_details',
        )
        return qs


class OrganisationPeopleView(generics.ListAPIView):
    """
    Return un-paginated organisation people list
    """
    serializer_class = OrganisationPeopleSerializer
    pagination_class = None
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        position = self.request.user.person.primary_dod_position
        if not position:
            return None
        return position.organisation.organisation_people.prefetch_related(
            'person__details', 'person__details__title',
        ).filter(
            role__code_name__in=['FCR', 'OPP', ],
        ).all()
