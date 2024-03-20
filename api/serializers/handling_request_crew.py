from rest_framework import serializers
from handling.models import HandlingRequest, HandlingRequestCrew, HandlingRequestCrewMemberPosition
from api.serializers.user import PersonSerializer
from api.utils.related_field import RelatedFieldAlternative
from handling.utils.validators import get_person_active_crews
from user.models import Person


class HandlingRequestCrewMemberPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlingRequestCrewMemberPosition
        fields = ['id', 'name', ]


class HandlingRequestCrewSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    position = HandlingRequestCrewMemberPositionSerializer(read_only=True)

    person_id = RelatedFieldAlternative(required=True,
                                        write_only=True,
                                        source='person',
                                        queryset=Person.objects.all())
    position_id = RelatedFieldAlternative(required=True,
                                          write_only=True,
                                          source='position',
                                          queryset=HandlingRequestCrewMemberPosition.objects.all())

    class Meta:
        model = HandlingRequestCrew
        read_only_fields = ['id', 'person', 'position', 'is_primary_contact', ]
        fields = [
            # GET Fields
            'id', 'person', 'position', 'is_primary_contact', 'can_update_mission',
            # POST Fields
            'person_id', 'position_id',
        ]

    def validate(self, data):
        # Get processing S&F Request ID
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        if handling_request_id:
            handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        else:
            # In case if PATCH request (i.e. updating existing crew row) get handling_request_id from its instance
            handling_request_id = self.instance.handling_request.pk
            handling_request = self.instance.handling_request

        # Check is user able to edit S&F Request in case if user is not staff
        request_user = getattr(self.context['request'], 'user')
        if not request_user.is_staff:
            request_person = getattr(request_user, 'person')
            position = request_person.primary_dod_position
            qs = position.get_sfr_list(managed=True)
            if not qs.filter(pk=handling_request_id).exists():
                raise serializers.ValidationError("S&F Request couldn't be updated")

        person = data.get('person')
        # Check overlap for existing S&F Requests and Mission
        overlapped_sfr, overlapped_missions = get_person_active_crews(
            person=person,
            arrival_date=handling_request.get_eta_date(),
            departure_date=handling_request.get_etd_date(),
            exclude_sfr=handling_request,
        )
        if overlapped_sfr:
            raise serializers.ValidationError(
                detail={'person_id': ["Person already in S&F Request crew for same date"]},
                code='invalid_value')
        if overlapped_missions:
            raise serializers.ValidationError(
                detail={'person_id': ["Person already in Mission crew for same date"]}, code='invalid_value')

        return data

    def create(self, validated_data, *args, **kwargs):
        handling_request_id = self.context.get('view').kwargs.get('handling_request_id')
        handling_request = HandlingRequest.objects.get(pk=handling_request_id)
        person = validated_data.get('person')

        organisation_people_qs = handling_request.customer_organisation.organisation_people.filter(person=person)
        if not organisation_people_qs.exists():
            raise serializers.ValidationError(
                detail={'person_id': ["Person does not belongs to S&F Request Organisation"]}, code='invalid_value')

        crew_qs = handling_request.mission_crew.filter(person=person)
        if crew_qs.exists():
            raise serializers.ValidationError(
                detail={'person_id': ["Person already in Crew"]}, code='invalid_value')

        instance = HandlingRequestCrew(
            **validated_data,
            handling_request_id=handling_request_id)
        instance.save()

        return instance

    def update(self, instance, validated_data):
        handling_request = instance.handling_request
        person = validated_data.get('person')

        organisation_people_qs = handling_request.customer_organisation.organisation_people.filter(person=person)
        if not organisation_people_qs.exists():
            raise serializers.ValidationError(
                detail={'person_id': ["Person does not belongs to S&F Request Organisation"]}, code='invalid_value')

        crew_qs = handling_request.mission_crew.filter(person=person).exclude(pk=instance.pk)
        if crew_qs.exists():
            raise serializers.ValidationError(
                detail={'person_id': ["Person already in Crew"]}, code='invalid_value')

        instance = super().update(instance, validated_data)
        return instance
