from django_select2 import forms as s2forms
from aircraft.models import AircraftType
from organisation.models.organisation import Organisation
from user.models import Person


class PersonPickWidget(s2forms.ModelSelect2Widget):
    model = Person
    search_fields = [
        "details__abbreviated_name__icontains",
        "details__contact_email__icontains",
        "details__first_name__icontains",
        "details__last_name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.fullname}')


class PeoplePickWidget(PersonPickWidget, s2forms.ModelSelect2MultipleWidget):
    pass


class PermissionsPickWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
        "codename__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class PersonGenderPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class PersonTitlePickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.name}')


class PersonPronounPickWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "subject_pronoun__icontains",
        "object_pronoun__icontains",
    ]

    def label_from_instance(self, obj):
        return str(f'{obj.subject_pronoun}/{obj.object_pronoun}')


class PersonAircraftTypesPickWidget(s2forms.ModelSelect2MultipleWidget):
    model = AircraftType
    search_fields = [
        "model__icontains",
        "designator__icontains",
        "manufacturer__icontains",
    ]


class PersonPositionAircraftTypesPickWidget(s2forms.ModelSelect2MultipleWidget):
    '''
    This widget returns Organisation Aircraft Types if it exists otherwise
    it will return all Aircraft Types.
    Should be used with customised assets/js/select2.js on a page.
    '''
    model = AircraftType
    dependent_fields = {'organisation': 'organisations'}
    search_fields = [
        "model__icontains",
        "designator__icontains",
        "manufacturer__icontains",
    ]

    def filter_queryset(self, request, term, queryset, **kwargs):
        organisations = kwargs.get('organisations', None)
        organisation = Organisation.objects.filter(pk=organisations).first()

        if organisation and organisation.aircraft_types.exists():
            qs = super().filter_queryset(request, term, queryset, **kwargs)
        else:
            qs = super().filter_queryset(request, term, queryset)
        return qs
