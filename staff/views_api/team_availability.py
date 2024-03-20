from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from datetime import datetime
from ..models.team_availability import EntryType
from ..serializers.team_availability import (SpecificEntrySerializer, BlanketEntrySerializer,
                                            PersonEntrySerializer, EntryTypeSerializer,
                                            CountrySerializer, AMLTeamSerializer, PersonTeamSerializer)
from user.models.person import Person
from organisation.models.organisation_people import OrganisationPersonTeam, OrganisationAMLTeam, OrganisationPeople
import json
from datetime import datetime, date
import holidays
from core.models.country import Country
from ..utils.team_availability import EntryEditMixin

class PeopleEntriesViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = PersonEntrySerializer
    queryset = Person.objects.none()
    renderer_classes = [JSONRenderer]
    pagination_class = None

    def get_queryset(self):
        queryset = Person.objects.filter(teams__isnull = False).distinct()
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        year = date.today().year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        teams = OrganisationPersonTeam.objects.all() # OR filter is_primary_assignment=True
        serializer = self.get_serializer(queryset, many=True, context={'start_date': start_date, 'end_date': end_date,
                                                                       'teams': teams.values_list('aml_team__name', flat=True)})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def people_list(self, request, *args, **kwargs):
        people_in_teams = OrganisationPersonTeam.objects.all()
        return Response(PersonTeamSerializer(people_in_teams, many=True).data)

    @action(detail=False, methods=["get"])
    def teams(self, request, *args, **kwargs):
        body_unicode = request.body.decode('utf-8')

        teams = OrganisationAMLTeam.objects.all()
        return Response(AMLTeamSerializer(teams, many=True).data)

    # I feel like it's a better design to have two separate endpoints and not base shape of return (holidays)
    # on the data we post (in this case: details true or false)
    @action(detail=False, methods=["get"])
    def countries(self, request, *args, **kwargs):
        people = OrganisationPeople.objects.filter(person__teams__isnull = False).distinct()
        countries = people.values('primary_region__country')
        supported_countries = holidays.list_supported_countries()
        queryset = Country.objects.filter(id__in = countries)

        serializer = CountrySerializer(queryset, fields=('name', 'code', 'regions'), many=True,
                                       context={'supported_countries': supported_countries, 'details': False})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def details(self, request, *args, **kwargs):
        body_unicode = request.body.decode('utf-8')

        start_date = datetime.strptime(json.loads(body_unicode)['start_date'], '%Y-%m-%d',).date()
        end_date = datetime.strptime(json.loads(body_unicode)['end_date'], '%Y-%m-%d').date()
        countries = json.loads(body_unicode)['countries'] # Format: country names
        supported_countries = holidays.list_supported_countries()
        queryset = Country.objects.filter(name__in = countries, code__in = supported_countries.keys())

        serializer = CountrySerializer(queryset, many=True,
                                       context={'supported_countries': supported_countries, 'details': True,
                                                'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def entry_types(self, request, *args, **kwargs):
        queryset = EntryType.objects.all()
        serializer = EntryTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def valid_entries(self, request):
        body_unicode = request.body.decode('utf-8')

        start_date = datetime.strptime(json.loads(body_unicode)['start_date'], '%Y-%m-%d',).date()
        end_date = datetime.strptime(json.loads(body_unicode)['end_date'], '%Y-%m-%d').date()
        teams = json.loads(body_unicode).get('teams')
        queryset = self.filter_queryset(self.get_queryset())
        serializer = PersonEntrySerializer(queryset, many=True,
                                           context={'start_date': start_date, 'end_date': end_date, 'teams': teams})

        return Response(status=status.HTTP_200_OK, data=serializer.data)


class SpecificEntryViewSet(CreateModelMixin, EntryEditMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = SpecificEntrySerializer
    queryset = None
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, ]
    pagination_class = None


class BlanketEntryViewSet(CreateModelMixin, EntryEditMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = BlanketEntrySerializer
    queryset = None
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser, ]
    pagination_class = None
