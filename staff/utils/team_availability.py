from datetime import datetime, date, timedelta
from rest_framework import serializers
from django.db import IntegrityError
from django.db.models import Q
from ..models.team_availability import SpecificEntry, BlanketEntry
from rest_framework.decorators import action
from rest_framework.response import Response


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class EntryEditMixin():

    def get_serializer(self, *args, **kwargs):
        # Force the usage of EntryBulkListSerializer, so that we have the same logic for singular entries as well
        # as bulk_ can handle saving singular entry, but it has to be in a list
        # if isinstance(kwargs.get("data", {}), list):
        kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

    # Delete, but it is actually a partial update for certain cases
    @action(detail=False, methods=["delete"])
    def delete(self, request, *args, **kwargs):
        partial = True # Always partial, we just flip a flag and optionally rearrange
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_delete(serializer)
        return Response(serializer.data)

    def perform_delete(self, serializer):
        serializer.delete()

    # Calling this edit, because even though we don't have an UpdateMixin, the router still does not let go of the url
    @action(detail=False, methods=["patch"])
    def edit(self, request, *args, **kwargs):
        partial = True # Always partial, we wouldn't modify person for example or wouldn't care about auxiliary fields
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_edit(serializer)
        return Response(serializer.data)

    def perform_edit(self, serializer):
        serializer.edit()

    @action(detail=False, methods=["patch"])
    def action(self, request, *args, **kwargs):
        partial = True # Always partial, we just flip a flag
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        action_list = self.perform_action(serializer)
        return Response(action_list)

    def perform_action(self, serializer):
        return serializer.action()

class EntryValidationMixin():

    def validate(self, data):
        requesting_user = self.context['request'].user
        requesting_person = requesting_user.person
        requested_user = data.get('person').user
        requested_person = data.get('person')
        team = data.get('team')
        requested_person_team = requested_person.teams.filter(aml_team__name__icontains = team)
        time_now = datetime.now()

        if team is None:
            raise serializers.ValidationError(
                f"{requested_person.fullname} is not part of any team")
        elif not requested_person_team.exists():
            raise serializers.ValidationError(
                f"{requested_person.fullname} is not part of the {team}")

        # When editing for another person...
        if requesting_person != requested_person:
            # Using builtin roles so that a given person does not necessarily have to be part of a team to have
            # permission to manage their schedule
            is_team_admin = requesting_user.roles.filter(name__icontains = team).exists()
            is_hun_admin = requesting_user.roles.filter(name__icontains = 'HUN').exists()
            is_general_admin = requesting_user.roles.filter(name__icontains = 'General').exists()
            # I don't know why one person can be part of multiple organisations...
            # In this case I assume that the person is Hungarian if they have one primary_region in Hungary
            requesting_person_is_hungarian = \
                requesting_person.organisation_people.filter(primary_region__country__name = 'Hungary').exists()
            requested_person_is_hungarian = \
                requested_person.organisation_people.filter(primary_region__country__name = 'Hungary').exists()

            # For now, admins can alter each other's entries (we have logs anyway)
            if requested_person_team[0].manages_own_schedule:
                raise serializers.ValidationError(
                    f"Cannot add or modify entries for {requested_person.fullname} as they manage their own schedule within the {team}.")

            if not is_team_admin and not is_general_admin:
                raise serializers.ValidationError(
                    f"Cannot add or modify entries for {requested_person.fullname} as you don't have permission to alter {team} entries.")

            if requested_person_is_hungarian and not requesting_person_is_hungarian:
                raise serializers.ValidationError(
                    f"{requested_person.fullname}'s schedule can only be altered by Hungarian Staff Admins.")

            if requested_person_is_hungarian and not is_hun_admin and not is_team_admin:
                raise serializers.ValidationError(
                    f"No permission to alter {requested_person.fullname}'s schedule.")

        # Self-approve if a person manages their own schedule within a team
        if not 'action' in self.context['request'].META['PATH_INFO']:
            if requested_person_team[0].manages_own_schedule or requesting_person != requested_person:
                data['is_approved'] = True
                data['is_disapproved'] = False
                data['action_by'] = requesting_person
                data['action_on'] = time_now
            else:
                data['is_approved'] = False
                data['is_disapproved'] = False
                data['action_by'] = None
                data['action_on'] = None

            data['created_on'] = time_now
        else:
            # Disallow own entry approval / disapproval
            if not is_team_admin and not is_general_admin or requested_person_is_hungarian and not is_hun_admin:
                raise serializers.ValidationError(
                    f"Cannot approve or disapprove your own entry")

        return data


# Not going to check unsaved entries, nobody is going to edit the payload, it's an in-house app
class EntryBulkListSerializer(serializers.ListSerializer):
    def create(self, validated_data):

        requesting_person = getattr(self.context['request'].user, 'person')
        results = []
        start_date = validated_data[0]['start_date']
        end_date = validated_data[0]['end_date']
        start_hour = validated_data[0]['start_hour']
        end_hour = validated_data[0]['end_hour']
        people = []
        teams = []
        entry_types = []
        error_list = []
        model = self.child.Meta.model

        # Get data for filter, get the most broad range of entries
        for attrs in validated_data:

            attrs['created_by'] = requesting_person
            attrs['flagged_for_edit'] = False
            attrs['flagged_for_delete'] = False
            attrs['original_entry'] = None
            attrs['updated_on'] = None
            attrs['updated_by'] = None
            if attrs['action_on'] is not None:
                attrs['created_on'] = attrs['action_on']

            if attrs['start_date'] < start_date:
                start_date = attrs['start_date']
            if attrs['end_date'] > end_date:
                start_date = attrs['end_date']
            if attrs['start_hour'] < start_hour:
                start_hour = attrs['end_hour']
            if attrs['end_hour'] > end_hour:
                end_hour = attrs['end_hour']
            entry_types.append(attrs['entry_type'])
            people.append(attrs['person'])
            teams.append(attrs['team'])

        hour_query = interval_query('start_hour', 'end_hour', start_hour, end_hour, False)
        date_query = interval_query('start_date', 'end_date', start_date, end_date, False)

        existing_entries = self.child.Meta.model.objects.filter(Q(person__in = people),
                                                        Q(team__in = teams),
                                                        Q(entry_type__in = entry_types),
                                                        date_query, hour_query)

        for attrs in validated_data:
            date_overlap_error = False
            hour_query = interval_query('start_hour', 'end_hour', attrs['start_hour'], attrs['end_hour'], False)
            common_queries = (Q(person = attrs['person']), Q(team = attrs['team']),
                              Q(entry_type = attrs['entry_type']), Q(hour_query))
            date_query = interval_query('start_date', 'end_date', attrs['start_date'], attrs['end_date'], False)

            if model == SpecificEntry:
                applied_date_query = Q(applied_on_dates__overlap = attrs['applied_on_dates'])
                filtered_entries = existing_entries.filter(*common_queries, date_query, applied_date_query)
                attrs['start_date'] = \
                    date(attrs['start_date'].year, attrs['start_date'].month, attrs['applied_on_dates'][0])
                attrs['end_date'] = \
                    date(attrs['end_date'].year, attrs['end_date'].month, attrs['applied_on_dates'][-1])

                validate_exchange(attrs, error_list)

            else:
                filtered_entries = existing_entries.filter(*common_queries, date_query)

                # Check if there are other entries of the same type that we would overlap with
                for entry in filtered_entries:
                    entry_dates = get_applicable_dates(entry.start_date, entry.end_date,
                                                       entry.applied_on_days, entry.applied_on_weeks)
                    new_dates = get_applicable_dates(attrs['start_date'], attrs['end_date'],
                                                     attrs['applied_on_days'], attrs['applied_on_weeks'])

                    if set(entry_dates).intersection(set(new_dates)):
                        date_overlap_error = True

            if not filtered_entries.exists() and not date_overlap_error:
                attrs['id'] = None
                results.append(model(**attrs))
            elif filtered_entries.exists() or date_overlap_error:
                error_list.append({'message': 'Save Aborted because of a conflicting entry',
                                   'new_entry': {**entry_details(attrs)},
                                   'original_entry': {**entry_details(filtered_entries[0], True)}})

        if error_list:
            raise serializers.ValidationError(error_list)
        else:
            try:
                self.child.Meta.model.objects.bulk_create(results)
            except IntegrityError as e:
                raise serializers.ValidationError(e)

        return results

    # Custom delete, we don't get validated data from serializer.save()
    # Assume we get data shaped as the DB entry, but modified as to what to delete. e.g: applied_on_dates = [1,2,3,4,5]
    # We get: [1,2,3], so we modify original to [4,5]
    # It is mandatory to get applied_on_dates / applied_on_days OR applied_on_weeks
    # It is important to get start_date, end_date for blanket entries, else we can figure them out for specific entries
    def delete(self):

        requesting_person = getattr(self.context['request'].user, 'person')
        time_now = datetime.now()
        model = self.child.Meta.model
        result = []
        error_list = []
        whole_range_affected = False

        # Not the best solution, as it is an n+1 query, but I can assume that we won't delete that many entries / run
        for attrs in self.validated_data:

            if attrs['flagged_for_edit']:
                continue

            original_entry = model.objects.filter(id = attrs['id'], team = attrs['team'], person = attrs['person'])

            if not original_entry.exists():
                error_list.append({'message': 'The following entry is not found',
                                   'new_entry': {**entry_details(attrs)}})
                continue
            else:
                original_entry = original_entry[0]

                if original_entry.is_disapproved:
                    error_list.append({'message': 'Cannot delete a disapproved entry',
                                       'original_entry': {**entry_details(original_entry, True)}})
                    continue

                if not original_entry.is_approved:
                    attrs['is_approved'] = True
                    attrs['action_on'] = time_now
                    attrs['action_by'] = requesting_person

                start_date = original_entry.start_date
                end_date = original_entry.end_date
                attrs['created_by'] = requesting_person # For when we duplicate entries
                attrs['id'] = None # Only used to get original entry

                manages_own_schedule = attrs['person'].teams.filter(aml_team = attrs['team'])[0].manages_own_schedule

                if model == SpecificEntry:
                    new_dates = attrs.get('applied_on_dates')

                    if new_dates is None:
                        error_list.append({'message': 'Need to mark at least one date for deletion',
                                           'original_entry': {**entry_details(original_entry, True)},
                                           'new_entry': {**entry_details(attrs)}})
                        continue
                    new_dates = set(new_dates)

                    if set(original_entry.applied_on_dates) == new_dates:
                        whole_range_affected = True

                    validate_exchange(attrs, error_list)

                else:
                    new_days = attrs.get('applied_on_days')
                    new_weeks = attrs.get('applied_on_weeks')

                    if new_days is None:
                        error_list.append({'message': 'Need to mark at least one day for deletion',
                                           'original_entry': {**entry_details(original_entry, True)},
                                           'new_entry': {**entry_details(attrs)}})
                        if new_weeks is not None:
                            continue

                    if new_weeks is None:
                        error_list.append({'message': 'Need to mark at least one week for deletion',
                                           'original_entry': {**entry_details(original_entry, True)},
                                           'new_entry': {**entry_details(attrs)}})
                        continue

                    new_days = set(new_days)
                    new_weeks = set(new_weeks)

                    if set(original_entry.applied_on_days) == set(new_days) and\
                       set(original_entry.applied_on_weeks) == set(new_weeks):
                         whole_range_affected = True

                # New entry is not needed
                if whole_range_affected:
                    if manages_own_schedule:
                        original_entry.delete()
                    else:
                        original_entry.flagged_for_delete = True
                        original_entry.updated_on = time_now
                        original_entry.updated_by = requesting_person

                        # Force approval of yet to be approved entries on deletion
                        if not original_entry.is_approved:
                            original_entry.is_approved = True

                        original_entry.save()
                else:
                    # Throw away additional dates/days/weeks not present originally
                    if model == SpecificEntry:
                        # Force dates for SpecificEntry, but not for blanket entries as it is not obvious
                        new_dates = set(attrs.get('applied_on_dates'))
                        attrs['applied_on_dates'] = [x for x in new_dates if x in original_entry.applied_on_dates]
                        original_entry.applied_on_dates = \
                            [x for x in original_entry.applied_on_dates if x not in new_dates]
                        original_entry.start_date = \
                            date(start_date.year, start_date.month, original_entry.applied_on_dates[0])
                        original_entry.end_date = \
                            date(end_date.year, end_date.month, original_entry.applied_on_dates[-1])
                    else:
                        if new_days != set(original_entry.applied_on_days):
                            attrs['applied_on_days'] = [x for x in new_days if x in original_entry.applied_on_days]
                            original_entry.applied_on_days = \
                                [x for x in original_entry.applied_on_days if x not in new_days]

                        if new_weeks != set(original_entry.applied_on_weeks):
                            attrs['applied_on_weeks'] = [x for x in new_weeks if x in original_entry.applied_on_weeks]
                            original_entry.applied_on_weeks = \
                                [x for x in original_entry.applied_on_weeks if x not in new_weeks]

                    # New entry is needed for when a person manages their own schedule, but we reuse the original one
                    original_entry.save()

                    if not manages_own_schedule:
                        # original_entry.save()
                        attrs['original_entry'] = original_entry
                        attrs['flagged_for_delete'] = True

                        # New Entry
                        if model == SpecificEntry:
                            attrs['start_date'] = \
                                date(attrs['start_date'].year, attrs['start_date'].month, attrs['applied_on_dates'][0])
                            attrs['end_date'] = \
                                date(attrs['end_date'].year, attrs['end_date'].month, attrs['applied_on_dates'][-1])
                        result.append(model(**attrs))

        if error_list:
            raise serializers.ValidationError(error_list)
        else:
            try:
                self.child.Meta.model.objects.bulk_create(result)
            except IntegrityError as e:
                raise serializers.ValidationError(e)

        return result

    # What I expect: an entry that replaces the original entry entirely or partly (+/- log keeping)
    def edit(self):
        requesting_person = getattr(self.context['request'].user, 'person')
        time_now = datetime.now()
        model = self.child.Meta.model
        result = []
        error_list = []
        whole_range_affected = False
        team_error = False

        # Not the best solution, as it is an n+1 query, but I can assume that we won't edit that many entries / run
        for attrs in self.validated_data:

            if attrs['flagged_for_delete']:
                continue

            attrs['flagged_for_edit'] = False # because the received entry will be the new entry
            manages_own_schedule = False
            original_entry = model.objects.filter(id = attrs['id'], team = attrs['team'], person = attrs['person'])

            if not original_entry.exists():
                error_list.append({'message': 'The following entry is not found',
                                   'original_entry': {**entry_details(attrs)}})
                continue
            else:
                manages_own_schedule = attrs['person'].teams.filter(aml_team = attrs['team'])[0].manages_own_schedule

                original_entry = original_entry[0]
                if not original_entry.is_approved or original_entry.is_disapproved:
                    error_list.append({'message': 'Only approved entries can be edited',
                                       'original_entry': {**entry_details(original_entry, True)}})
                    continue

                original_entry.updated_on = time_now
                original_entry.updated_by = requesting_person
                start_date = original_entry.start_date
                end_date = original_entry.end_date
                attrs['created_by'] = requesting_person # For when we duplicate entries
                attrs['id'] = None # Only used to get original entry

                if model == SpecificEntry:
                    original_dates = set(original_entry.applied_on_dates)
                    new_dates = set(attrs['applied_on_dates'])
                    if original_dates == new_dates:
                         whole_range_affected = True

                    if not original_dates.intersection(new_dates):
                        error_list.append({'message': 'Mismatch between the new and the original entry',
                                           'new_entry': {**entry_details(attrs)},
                                           'original_entry': {**entry_details(original_entry, True)}})
                        continue

                    # Force correct new entry dates
                    attrs['start_date'] = \
                            date(attrs['start_date'].year, attrs['start_date'].month, attrs['applied_on_dates'][0])
                    attrs['end_date'] = \
                            date(attrs['end_date'].year, attrs['end_date'].month, attrs['applied_on_dates'][-1])

                    if attrs.get('replaces_other_entry'):
                        error_list.append({'message': 'Cannot edit an exchanged entry',
                                           'new_entry': {**entry_details(attrs)},
                                           'original_entry': {**entry_details(attrs.get('replaces_other_entry'), True)}})

                    elif attrs.get('replaces_own_entry'):
                        validate_exchange(attrs, error_list)

                else:
                    original_days = set(original_entry.applied_on_days)
                    new_days = set(attrs['applied_on_days'])
                    original_weeks = set(original_entry.applied_on_weeks)
                    new_weeks = set(attrs['applied_on_weeks'])

                    if original_days == new_days and original_weeks == new_weeks:
                         whole_range_affected = True

                    if not original_days.intersection(new_days) or not original_weeks.intersection(new_weeks):
                        error_list.append({'message': 'Mismatch between the new and the original entry',
                                           'new_entry': {**entry_details(attrs)},
                                           'original_entry': {**entry_details(original_entry, True)}})
                        continue

                if whole_range_affected:
                    if manages_own_schedule:
                        attrs['id'] = original_entry.id
                        original_entry.delete()
                    else:
                        attrs['original_entry'] = original_entry
                        original_entry.flagged_for_edit = True
                        original_entry.save()
                else:
                    if model == SpecificEntry:
                        # Reorganize original entry
                        original_entry.applied_on_dates = \
                            [x for x in original_entry.applied_on_dates if x not in new_dates]
                        original_entry.start_date = \
                            date(start_date.year, start_date.month, original_entry.applied_on_dates[0])
                        original_entry.end_date = \
                            date(end_date.year, end_date.month, original_entry.applied_on_dates[-1])
                    else:
                        original_entry.applied_on_days = \
                            [x for x in original_entry.applied_on_days if x not in new_days]
                        original_entry.applied_on_weeks = \
                            [x for x in original_entry.applied_on_weeks if x not in new_weeks]

                    if not manages_own_schedule:
                        original_entry.flagged_for_edit = False
                        attrs['original_entry'] = original_entry

                    original_entry.save()
                result.append(model(**attrs))

        if error_list:
            raise serializers.ValidationError(error_list)
        else:
            try:
                self.child.Meta.model.objects.bulk_create(result)
            except IntegrityError as e:
                raise serializers.ValidationError(e)

        return result


    def action(self):
        requesting_person = getattr(self.context['request'].user, 'person')
        model = self.child.Meta.model
        error_list = []
        approve_list = []
        disapprove_list = []
        moved_entries = []
        time_now = datetime.now()

        for attrs in self.validated_data:
            id = attrs.get('id')

            if id is None:
                error_list.append({'message': 'Missing ID detected'})
                continue

            # If both approved and disapproved for some reason -> force approval
            if attrs.get('is_approved'):
                approve_list.append(attrs['id'])
            elif attrs.get('is_disapproved'):
                disapprove_list.append(attrs['id'])

        if error_list:
            raise serializers.ValidationError(error_list)

        # Approve
        approved_entries = model.objects.filter(id__in = approve_list)
        approved_entries.update(is_approved=True, is_disapproved=False,
                                action_on=time_now, action_by=requesting_person)

        # Disapprove - move back entry to parent on delete / edit!
        disapproved_entries = model.objects.filter(id__in = disapprove_list)
        disapproved_entries.update(is_approved=False, is_disapproved=True,
                                   action_on=time_now, action_by=requesting_person)

        for entry in disapproved_entries:
            if model == SpecificEntry and entry.original_entry is not None:
                from ..serializers.team_availability import SpecificEntrySerializer
                original_entry = entry.original_entry

                original_entry.applied_on_dates = \
                    list(set(entry.applied_on_dates).union(set(original_entry.applied_on_dates)))
                original_entry.start_date = date(original_entry.start_date.year,
                                                 original_entry.start_date.month,
                                                 original_entry.applied_on_dates[0])
                original_entry.end_date = date(original_entry.end_date.year,
                                               original_entry.end_date.month,
                                               original_entry.applied_on_dates[-1])
                original_entry.save()

                moved_entries.append({'new_entry': SpecificEntrySerializer(entry, many=False).data,
                                      'original_entry': SpecificEntrySerializer(original_entry, many=False).data})

            elif model == BlanketEntry and entry.original_entry is not None:
                from ..serializers.team_availability import BlanketEntrySerializer
                original_entry = entry.original_entry

                original_entry.applied_on_days = \
                    list(set(entry.applied_on_days).union(set(original_entry.applied_on_days)))
                original_entry.applied_on_weeks = \
                    list(set(entry.applied_on_weeks).union(set(original_entry.applied_on_weeks)))
                original_entry.save()

                moved_entries.append({'new_entry': BlanketEntrySerializer(entry, many=False).data,
                                      'original_entry': BlanketEntrySerializer(original_entry, many=False).data})

        return {'approved': approve_list, 'disapproved': disapprove_list, 'moved_entries': moved_entries}


# https://stackoverflow.com/questions/59533698/finding-overlapping-dates-in-a-specific-range-in-django
def interval_query(start_date_column, end_date_column_name, start_dt, end_dt,
                                                   closed_interval=True):
    """
    Creates a query for finding intervals in the Django model which overlap the [start_date, end_date] closed interval.
    It also takes care of the invalid interval case when start date > end date for both stored ones and the input ones.

    :param start_date_column: name of start date column in the model
    :param end_date_column_name: name of end date column in the model
    :param start_dt: start date of the interval to be checked
    :param end_dt: end date of the interval to be checked
    :param closed_interval: closed interval = True means intervals are of the form [start, end],
     otherwise intervals are of the form [start, end). Where ")" means end-value is included and ")" end-value is not
    included.
    :return:
    """

    q_start_dt__gt = f'{start_date_column}__gt'
    q_start_dt__gte = f'{start_date_column}__gte'
    q_start_dt__lt = f'{start_date_column}__lt'
    q_start_dt__lte = f'{start_date_column}__lte'
    q_end_dt__gt = f'{end_date_column_name}__gt'
    q_end_dt__gte = f'{end_date_column_name}__gte'
    q_end_dt__lt = f'{end_date_column_name}__lt'
    q_end_dt__lte = f'{end_date_column_name}__lte'


    q_is_contained = Q(**{q_start_dt__gte: start_dt}) & Q(**{q_end_dt__lte: end_dt}) # is_inside
    q_contains = Q(**{q_start_dt__lte: start_dt}) & Q(**{q_end_dt__gte: end_dt}) # is_overlaps
    q_slides_before = Q(**{q_start_dt__lt: start_dt}) & Q(**{q_end_dt__lt: end_dt}) # start edge
    q_slides_after = Q(**{q_start_dt__gt: start_dt}) & Q(**{q_end_dt__gt: end_dt}) # end edge
    if closed_interval:
        q_slides_before = q_slides_before & Q(**{q_end_dt__gte: start_dt})
        q_slides_after = q_slides_after & Q(**{q_start_dt__lte: end_dt})
    else:
        q_slides_before = q_slides_before & Q(**{q_end_dt__gt: start_dt})
        q_slides_after = q_slides_after & Q(**{q_start_dt__lt: end_dt})

    return q_contains | q_is_contained | q_slides_before | q_slides_after


def entry_details(attrs, model=False):
    if model:
        if hasattr(attrs, 'applied_on_dates'):
            fields = {'applied_on_dates': attrs.applied_on_dates}
        else:
            fields = {'applied_on_days': attrs.applied_on_days, 'applied_on_weeks': attrs.applied_on_weeks}

        return {'person': attrs.person.fullname, 'team': attrs.team.name,
                'start_date': attrs.start_date, 'end_date': attrs.end_date,
                'start_hour': attrs.start_hour, 'end_hour': attrs.end_hour,
                **fields}
    else:
        if attrs.get('applied_on_dates') is not None:
            fields = {'applied_on_dates': attrs.get('applied_on_dates')}
        else:
            fields = {'applied_on_days': attrs.get('applied_on_days'), 'applied_on_weeks': attrs.get('applied_on_weeks')}

        return {'person': attrs['person'].fullname, 'team': attrs['team'].name,
                'start_date': attrs['start_date'], 'end_date': attrs['end_date'],
                'start_hour': attrs['start_hour'], 'end_hour': attrs['end_hour'],
                **fields}


def get_applicable_dates(start_date, end_date, days, weeks):
    occupied_dates = []
    loop_end_date = end_date + timedelta(days=1)
    current_date = start_date
    week_number = 0 if weeks[0] == 0 else 1

    while current_date != loop_end_date:
        if current_date.isoweekday() in days and week_number in weeks:
            occupied_dates.append(current_date)

        if current_date.isoweekday() == 7 and not week_number == 0:
            week_number += 1
        current_date += timedelta(days=1)

    return occupied_dates


def validate_exchange(attrs, error_list):
    time_now = datetime.now()

    # A person can replace their own entry too, essentially override blanket entries on an ad-hoc basis
    # Only if provided via 'replaces_own_entry'
    replaced_entry = attrs.get('replaces_other_entry')
    replaced_own_entry = attrs.get('replaces_own_entry')

    if replaced_own_entry is not None:
        if replaced_own_entry.person != attrs['person']:
            error_list.append({'message': 'The provided schedule does not belong to the person requesting the exchange',
                               'new_entry': {**entry_details(attrs)},
                               'original_entry': {**entry_details(replaced_own_entry, True)}})

            replaced_own_entry_dates = \
                get_applicable_dates(replaced_own_entry.start_date, replaced_own_entry.end_date,
                                     replaced_own_entry.applied_on_days, replaced_own_entry.applied_on_weeks)

            for specific_date in attrs['applied_on_dates']:
                new_date = date(attrs['start_date'].year, attrs['end_date'].month, specific_date)

                if new_date not in replaced_own_entry_dates:
                    if new_date not in replaced_entry_dates:
                        error_list.append({'message': f'{new_date} is missing from the your original entry',
                                           'new_entry': {**entry_details(attrs)},
                                           'original_entry': {**entry_details(replaced_own_entry, True)}})

    if replaced_entry is not None:

        if replaced_entry.person == attrs['person']:
            error_list.append({'message': 'The entry to be replaced shouldn\'t belong to the person requesting the exchange',
                               'new_entry': {**entry_details(attrs)},
                               'original_entry': {**entry_details(replaced_entry, True)}})

        if replaced_own_entry is None:
            error_list.append({'message': 'Missing a schedule entry that is going to get replaced',
                               'new_entry': {**entry_details(attrs)},
                               'replaced_entry': {**entry_details(replaced_entry, True)}})

        replaced_entry_dates = get_applicable_dates(replaced_entry.start_date, replaced_entry.end_date,
                                                    replaced_entry.applied_on_days, replaced_entry.applied_on_weeks)

        for specific_date in attrs['applied_on_dates']:
            new_date = date(attrs['start_date'].year, attrs['end_date'].month, specific_date)

            if new_date not in replaced_entry_dates:
                error_list.append({'message': f'{new_date} is missing from the other person\'s entry',
                                   'new_entry': {**entry_details(attrs)},
                                   'replaced_entry': {**entry_details(replaced_entry, True)}})

            # Can only do whole days and only if hours are the same (else it's not administered)
            replaced_own_start_hour = datetime.combine(date.today(), replaced_own_entry.start_hour)
            replaced_own_end_hour = datetime.combine(date.today(), replaced_own_entry.end_hour)
            replaced_start_hour = datetime.combine(date.today(), replaced_entry.start_hour)
            replaced_end_hour = datetime.combine(date.today(), replaced_entry.end_hour)

            if replaced_own_end_hour - replaced_own_start_hour != replaced_end_hour - replaced_start_hour:
                error_list.append({'message': 'Can only exchange a whole day\'s schedule',
                                   'new_entry': {**entry_details(attrs)},
                                   'original_entry': {**entry_details(replaced_own_entry, True)},
                                   'replaced_entry': {**entry_details(replaced_entry, True)}})

            # Force the other entry's attributes on the newly created exchanged entry
            attrs['start_hour'] = replaced_entry.start_hour
            attrs['end_hour'] = replaced_entry.end_hour
            attrs['entry_type'] = replaced_entry.entry_type

            manages_own_schedule = \
                attrs['person'].teams.filter(aml_team = attrs['team'])[0].manages_own_schedule
            other_person_manages_own_schedule = \
                attrs['person'].teams.filter(aml_team = attrs['team'])[0].manages_own_schedule

            if manages_own_schedule != other_person_manages_own_schedule:
                error_list.append({'message': 'Can only exchange schedules if both participants\' schedule is managed by an admin or they both manage their own schedules',
                                   'new_entry': {**entry_details(attrs)},
                                   'original_entry': {**entry_details(replaced_own_entry, True)},
                                   'replaced_entry': {**entry_details(replaced_entry, True)}})

            new_entry_date = datetime.combine(attrs['start_date'], attrs['start_hour'])
            next_day = time_now + timedelta(days=1)

            # Can't request on friday and on weekends
            if new_entry_date - time_now < timedelta(days=1) and not next_day.isoweekday() in [6,7,1]:
                error_list.append({'message': 'Can only exchange a schedule if the workday happens in the next 24 hours or later',
                                   'new_entry': {**entry_details(attrs)},
                                   'original_entry': {**entry_details(replaced_own_entry, True)},
                                   'replaced_entry': {**entry_details(replaced_entry, True)}})

    return error_list
