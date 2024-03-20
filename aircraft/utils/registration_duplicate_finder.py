from django.db.models import Count, Subquery, Max, Min, Q, F, Value, CharField, IntegerField, BooleanField, Case, When, OuterRef
from django.forms import ValidationError
import string
from aircraft.models import AircraftHistory


def validate_aircraft_registration(registration, exclude_instance=None, return_object=False):
    '''
    Aircraft validation function
    
    Input:
        - registration: char
        - exclude_instance: Aircraft instance, to exclude self from duplicate finding on object editing
        - return_object: boolean
        
    If True passed to the return_object: function will return duplicate object if it will be found
    otherwise string of the registration, this is means no duplicates found.
    '''
    
    # Try to validate fast
    # Works only with:
    # Input | Database
    # T-EST | TEST
    # TEST  | TEST
    # Not works with: 
    # Input | Database
    # TEST  | T-EST
    registration_without_punctuation = registration.translate(
        str.maketrans('', '', string.punctuation))
    search_qs = AircraftHistory.objects.filter(
                    Q(registration__iexact=registration) |
                    Q(registration__iexact=registration_without_punctuation)
                ).exclude(aircraft=exclude_instance)
    if search_qs.exists():
        if return_object:
            search_qs.first().aircraft
        else:
            raise ValidationError(
                "An active aircraft with this registration already exists in the AML database. \
                    Please update this aircraft record instead of trying to add a new one.")
    
    # Validate more accuracy but slowly
    # Remove punctuation in the input and all database values to compare it
    existings_registrations = AircraftHistory.objects.exclude(
        aircraft=exclude_instance).values_list('registration', flat=True)
    # Remove punctuation in existing database registrations
    existings_registrations_wo_punctuation = []
    for item in existings_registrations:
        item_wo_punctuation = item.translate(str.maketrans('', '', string.punctuation))
        existings_registrations_wo_punctuation.append(item_wo_punctuation)
    
    # Check compare input value against database values without punctuation
    if registration_without_punctuation in existings_registrations_wo_punctuation:
        if return_object:
            return search_qs.first().aircraft
        else:
            raise ValidationError(
                "An active aircraft with this registration already exists in the AML database. \
                    Please update this aircraft record instead of trying to add a new one.")
            
    return registration
