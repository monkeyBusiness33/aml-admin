from django.db import transaction
from rest_framework import serializers
from aircraft.models import Aircraft, AircraftHistory, AircraftType
from aircraft.utils.registration_duplicate_finder import validate_aircraft_registration
from api.serializers.airport import AirportSerializer
from api.serializers.operator import OperatorSerializer
from api.serializers.organisation import OrganisationSerializer
from organisation.models.organisation import Organisation


class AircraftTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AircraftType
        fields = ['id', 'designator', 'manufacturer', 'model', 'category', ]


class RelatedFieldAlternative(serializers.PrimaryKeyRelatedField):

        def __init__(self, **kwargs):
            self.serializer = kwargs.pop('serializer', None)
            if self.serializer is not None and not issubclass(self.serializer, serializers.Serializer):
                raise TypeError('"serializer" is not a valid serializer class')

            super().__init__(**kwargs)

        def use_pk_only_optimization(self):
            return False if self.serializer else True

        def to_representation(self, instance):
            if self.serializer:
                return self.serializer(instance, context=self.context).data
            return super().to_representation(instance)

        
class AircraftSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='details.id', read_only=True)
    operator_id = RelatedFieldAlternative(
        many=False, write_only=True, source='operator', queryset=Organisation.objects.aircraft_operator())
    operator = OperatorSerializer(many=False, read_only=True, source='details.operator')
    homebase = AirportSerializer(many=False, read_only=True, source='details.homebase')
    registration = serializers.CharField(source='details.registration')
    type = AircraftTypeSerializer(many=False, read_only=True)
    type_id = RelatedFieldAlternative(many=False, write_only=True, 
                                      required=False, source='type', 
                                      queryset=AircraftType.objects.all())

    class Meta:
        model = Aircraft
        fields = ['id', 'registration', 'type', 'type_id', 'operator_id',
                  'operator', 'homebase', ]
    
    def create(self, validated_data):
        registration = validated_data['details']['registration']
        
        validation_result = validate_aircraft_registration(
            registration=registration, return_object=True)
        
        # Get submitting user organisation Airport
        person = self.context['request'].user.person
        organisation_address_with_airport = person.organisations.filter(
            addresses__airport__isnull=False).values('addresses__airport__id').first()
        
        if organisation_address_with_airport:
            airport_id = organisation_address_with_airport[
                'addresses__airport__id']
        else:
            airport_id = None
        
        if isinstance(validation_result, Aircraft):
            aircraft = validation_result
        else:
            with transaction.atomic():
                aircraft = Aircraft()
                aircraft.type = validated_data.get('type', None)
                aircraft.save()
                aircraft_details = AircraftHistory()
                aircraft_details.aircraft = aircraft
                aircraft_details.registration = validated_data['details']['registration']
                aircraft_details.operator = validated_data['operator']
                aircraft_details.homebase_id = airport_id
                aircraft_details.save()
                aircraft.details = aircraft_details
                
        return aircraft


class TailNumberSerializer(serializers.ModelSerializer):
    homebase = AirportSerializer(many=False)
    operator = OrganisationSerializer()

    class Meta:
        model = AircraftHistory
        fields = ['id', 'registration', 'operator', 'homebase', ]
