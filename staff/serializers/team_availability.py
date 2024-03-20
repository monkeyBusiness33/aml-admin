from rest_framework import serializers
from ..models.team_availability import SpecificEntry, BlanketEntry, EntryType
from user.models.person import Person
from django.db.models import Q
from organisation.models.organisation_people import OrganisationPersonTeam, OrganisationPeople, OrganisationAMLTeam
from core.models.country import Country, Region
from django.db.models import F, Func, Value
from django.db.models.fields import CharField
import holidays
from ..utils.team_availability import (EntryValidationMixin, EntryBulkListSerializer,
                                       DynamicFieldsModelSerializer)


class SpecificEntrySerializer(EntryValidationMixin, serializers.ModelSerializer):

    id = serializers.IntegerField(required=False)
    action_by = serializers.StringRelatedField(source='action_by.fullname')

    class Meta:
        model = SpecificEntry
        fields = '__all__'
        list_serializer_class = EntryBulkListSerializer


class BlanketEntrySerializer(EntryValidationMixin, serializers.ModelSerializer):

    id = serializers.IntegerField(required=False)
    action_by = serializers.StringRelatedField(source='action_by.fullname')

    class Meta:
        model = BlanketEntry
        fields = '__all__'
        list_serializer_class = EntryBulkListSerializer


class TeamSerializer(serializers.ModelSerializer):
    team = serializers.StringRelatedField(source='aml_team.name')
    is_team_admin = serializers.SerializerMethodField()
    role = serializers.StringRelatedField(source='role.name')

    def get_is_team_admin(self, entry):
        if hasattr(entry.person, 'user'):
            return entry.person.user.roles.filter(Q(name=f'Staff Admin ({entry.aml_team.name})')).exists()
        return False

    class Meta:
        model = OrganisationPersonTeam
        fields = ['team', 'role', 'is_primary_assignment', 'manages_own_schedule', 'is_team_admin']


class AMLTeamSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganisationAMLTeam
        fields = ['id', 'name']


# I wanted to use the RelatedFieldAlternative but I have more options in this case for filtering
class PersonEntrySerializer(serializers.ModelSerializer):
    name = serializers.StringRelatedField(source='details')
    country = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    teams = serializers.SerializerMethodField()
    is_general_admin = serializers.SerializerMethodField()
    is_hun_admin = serializers.SerializerMethodField()
    specific_entries = serializers.SerializerMethodField()
    blanket_entries = serializers.SerializerMethodField()


    class Meta:
        model = Person
        fields = ['id', 'name', 'teams', 'country', 'region', 'is_general_admin', 'is_hun_admin',
                  'specific_entries', 'blanket_entries']

    def get_name(self, entry):
        return entry.details.fullname

    def get_teams(self, entry):
        teams = self.context['teams']
        if teams is None:
            return TeamSerializer(entry.teams.all(), many=True).data
        else:
            return TeamSerializer(entry.teams.filter(aml_team__name__in = teams), many=True).data

    def get_country(self, entry):
        org_person = OrganisationPeople.objects.filter(person = entry)
        if org_person.exists() and getattr(org_person[0], 'primary_region') is not None:
            return org_person[0].primary_region.country.name
        return None

    def get_region(self, entry):
        org_person = OrganisationPeople.objects.filter(person = entry)
        if org_person.exists() and getattr(org_person[0], 'primary_region') is not None:
            org_person = org_person[0]
            if org_person.primary_region.name == '':
                return org_person.primary_region.code.split('-')[1]
            return org_person.primary_region.name
        return None

    def get_is_general_admin(self, entry):
        if hasattr(entry, 'user'):
            return entry.user.roles.filter(name='Staff Admin (General)').exists()
        return False

    def get_is_hun_admin(self, entry):
        if hasattr(entry, 'user'):
            return entry.user.roles.filter(name='Staff Admin (HUN)').exists()
        return False

    def get_specific_entries(self, entry):
        start_date = self.context['start_date']
        end_date = self.context['end_date']
        teams = self.context['teams']

        if teams is None:
            # Always true
            team_query = ~Q(pk__in=[])
        else:
            team_query = Q(team__name__in = teams)

        queryset = SpecificEntry.objects.filter(Q(person = entry),
                                                team_query,
                                                Q(start_date__range = (start_date, end_date)) |
                                                Q(end_date__range= (start_date, end_date)))
        print('qs is', queryset)
        return SpecificEntrySerializer(queryset, many=True).data

    def get_blanket_entries(self, entry):
        start_date = self.context['start_date']
        end_date = self.context['end_date']
        teams = self.context['teams']

        if teams is None:
            # Always true
            team_query = ~Q(pk__in=[])
        else:
            team_query = Q(team__name__in = teams)

        queryset = BlanketEntry.objects.filter(Q(person = entry),
                                               team_query,
                                               Q(start_date__range = (start_date, end_date)) |
                                               Q(end_date__range= (start_date, end_date)))

        return BlanketEntrySerializer(queryset, many=True).data


class EntryTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = EntryType
        fields = '__all__'

class PersonTeamSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = OrganisationPersonTeam
        fields = ['id', 'name']

    def get_name(self, entry):
        print(entry)
        return f'{entry.person.fullname} - {entry.aml_team.name}'


class CountrySerializer(DynamicFieldsModelSerializer):
    regions = serializers.SerializerMethodField()
    holidays = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ['name', 'code', 'holidays', 'regions']

    def get_regions(self, entry):
        # Likely that Regions with names are important (we can't do much with a code, not user friendly)
        if self.context['details']:
            supported_countries = self.context['supported_countries']

            regions = Region.objects.annotate(region_code=Func(F('code'), Value('-'), Value(2),
                                              function='SPLIT_PART', output_field=CharField()))\
                                    .filter(country=entry, region_code__in = supported_countries.get(entry.code),
                                            name__isnull = False)\
                                    .exclude(name__exact = '')

            return RegionSerializer(regions,  many=True,
                                    context={'start_date': self.context['start_date'],
                                             'end_date': self.context['end_date']}).data
        else:
            regions = Region.objects.filter(country=entry, name__isnull = False).exclude(name__exact = '')
            return RegionSerializer(regions, fields=('name', 'code'), many=True).data


    def get_holidays(self, entry):
        start_date = self.context['start_date']
        end_date = self.context['end_date']
        years = set()
        years.add(start_date.year)
        years.add(end_date.year)

        all_holidays = holidays.country_holidays(entry.code, years=years)
        current_holidays = {}

        for date, holiday in sorted(all_holidays.items()):
            if date >= start_date and date <= end_date:
                current_holidays[str(date)] = holiday

        return current_holidays


class RegionSerializer(DynamicFieldsModelSerializer):
    code = serializers.SerializerMethodField()
    holidays = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['name', 'code', 'holidays']

    def get_code(self, entry):
        return f'{entry.code.split("-")[1]}'

    def get_holidays(self, entry):
        start_date = self.context['start_date']
        end_date = self.context['end_date']
        years = set()
        years.add(start_date.year)
        years.add(end_date.year)
        region_code = entry.code.split("-")[1]

        all_holidays = holidays.country_holidays(entry.country.code, subdiv=region_code, years=years)
        current_holidays = {}

        for date, holiday in sorted(all_holidays.items()):
            if date >= start_date and date <= end_date:
                current_holidays[str(date)] = holiday

        return current_holidays



