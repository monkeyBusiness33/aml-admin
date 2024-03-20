from rest_framework import generics, pagination
from rest_framework.renderers import JSONRenderer

from aircraft.models import AircraftType
from api.serializers.aircraft import AircraftSerializer, AircraftTypeSerializer
from api.serializers.airport import AirportSerializer
from api.serializers.core import UnitOfMeasurementSerializer, AirCardPrefixSerializer
from api.serializers.handling_base import HandlingLocationSerializer
from api.utils.filters import PrioritizedSearchFilter
from core.models import UnitOfMeasurement, AirCardPrefix
from organisation.models import Organisation


class AircraftTypesView(generics.ListAPIView):
    """
    View returns non paginated list of all Aircraft types
    """
    serializer_class = AircraftTypeSerializer
    pagination_class = None

    def get_queryset(self):
        organisation = self.request.user.person.main_organisation
        if organisation and organisation.is_military:
            qs = self.request.user.person.primary_dod_position.aircraft_types.all()
        else:
            qs = AircraftType.objects.all()

        return qs


class AirportsListView(generics.ListAPIView):
    """
    View returns non paginated list of all Airports
    """
    serializer_class = AirportSerializer
    queryset = Organisation.objects.airport().prefetch_related(
        'details',
        'airport_details',
    )
    pagination_class = None
    renderer_classes = [JSONRenderer]


class HandlingLocationsListView(generics.ListAPIView):
    """
    View returns non paginated list of S&F Request Locations
    """
    serializer_class = HandlingLocationSerializer
    queryset = Organisation.objects.handling_request_locations().prefetch_related(
        'details',
        'airport_details',
        'nasdl_details',
    )
    pagination_class = None
    renderer_classes = [JSONRenderer]


class ServicingAndFuelingLocationsListView(generics.ListAPIView):
    """
    View returns non paginated list of S&F Request Locations
    """
    serializer_class = HandlingLocationSerializer
    pagination.PageNumberPagination.page_size = 30
    renderer_classes = [JSONRenderer]
    filter_backends = [PrioritizedSearchFilter]

    search_fields = [
        'airport_details__icao_code',
        'airport_details__iata_code',
        'details__registered_name',
        'details__trading_name',
    ]

    def get_queryset(self):
        qs = Organisation.objects.handling_request_locations().prefetch_related(
            'details',
            'airport_details',
            'nasdl_details',
        )
        return qs


class QuantityUnitsListView(generics.ListAPIView):
    """
    View returns non paginated list of UnitOfMeasurement
    """
    serializer_class = UnitOfMeasurementSerializer
    queryset = UnitOfMeasurement.objects.filter(
        is_fluid_uom=True,
    )
    pagination_class = None


class UomListView(generics.ListAPIView):
    """
    View returns non paginated list of UnitOfMeasurement
    """
    renderer_classes = [JSONRenderer, ]
    serializer_class = UnitOfMeasurementSerializer
    queryset = UnitOfMeasurement.objects.filter(
        is_fluid_uom=True,
    ).order_by('id')
    pagination_class = None


class AircraftCreateView(generics.CreateAPIView):
    """
    Aircraft creation View
    """
    serializer_class = AircraftSerializer
    pagination_class = None
    renderer_classes = [JSONRenderer]


class AirCardPrefixesListView(generics.ListAPIView):
    """
    View returns non paginated list of AIR Card prefixes
    """
    serializer_class = AirCardPrefixSerializer
    queryset = AirCardPrefix.objects.with_state()
    pagination_class = None
    renderer_classes = [JSONRenderer]
