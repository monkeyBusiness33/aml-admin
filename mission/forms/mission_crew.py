from django import forms
from django.db.models import Q
from django.forms import widgets, BaseModelFormSet, modelformset_factory

from handling.form_widgets import PersonCrewDependentPickWidget, CrewMemberPositionPickWidget
from handling.utils.helpers import get_sfr_html_urls
from handling.utils.validators import get_person_active_crews
from mission.models import MissionCrewPosition
from mission.utils.helpers import get_mission_html_urls
from user.models import Person


class MissionCrewPositionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)
        self.fields['is_primary_contact'].widget.attrs['readonly'] = True
        self.fields['legs'].queryset = self.mission.legs.all()

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid

    class Meta:
        model = MissionCrewPosition
        fields = ['person', 'position', 'can_update_mission', 'is_primary_contact', 'legs']
        widgets = {
            "person": PersonCrewDependentPickWidget(attrs={
                'class': 'form-control required person-select',
                'data-minimum-input-length': 0,
            }),
            "position": CrewMemberPositionPickWidget(attrs={
                'class': 'form-control',
                'data-minimum-input-length': 0,
            }),
            "can_update_mission": widgets.CheckboxInput(attrs={
                'class': 'form-check-input can_update_mission',
            }),
            "is_primary_contact": widgets.CheckboxInput(attrs={
                'class': 'form-check-input exclusive is_primary_contact',
            }),
            "legs": widgets.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),
        }


class MissionCrewBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        organisation = getattr(self.mission, 'organisation')
        if self.mission:
            self.queryset = MissionCrewPosition.objects.filter(
                mission=self.mission).all()
        else:
            self.queryset = MissionCrewPosition.objects.none()

        for form in self.forms:
            form.fields['person'].queryset = Person.objects.filter(organisations=organisation)

            form.instance.mission = self.mission
            if form.instance.is_primary_contact:
                form.initial['can_update_mission'] = True
                form.instance.can_update_mission = True

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mission'] = self.mission
        return kwargs

    def clean(self):
        forms_to_delete = self.deleted_forms
        valid_forms = [
            form
            for form in self.forms
            if form.is_valid() and form not in forms_to_delete
        ]
        # Get id's for every instance selected to delete to exclude it in duplicate check
        instance_pks_to_delete = [form.instance.pk for form in forms_to_delete]
        people_to_save = []
        is_primary_contact_set = False
        start_date = self.mission.start_date
        end_date = self.mission.end_date

        # Set deleting user for activity_log record
        for form_to_delete in forms_to_delete:
            form_to_delete.instance.updated_by = self.request.user.person

        for form in valid_forms:
            person = getattr(form.instance, 'person', None)
            form.instance.updated_by = self.request.user.person
            is_primary_contact = getattr(form.instance, 'is_primary_contact', False)

            if form.instance.pk not in instance_pks_to_delete and person:
                # Create list of people to save for future validation
                people_to_save.append(person)
                # Trace is at least one person has set as primary contact
                if is_primary_contact:
                    is_primary_contact_set = True

            if person:
                # Exclude existing instance from duplicate checking versus self
                if form.instance.pk:
                    exclude_self_q = ~Q(pk=form.instance.pk)
                else:
                    exclude_self_q = ~Q()

                exclude_instances_to_delete_q = ~Q(pk__in=instance_pks_to_delete)
                crew_member = MissionCrewPosition.objects.filter(exclude_self_q, exclude_instances_to_delete_q,
                                                                 mission=self.mission,
                                                                 person=person)
                if crew_member.exists():
                    form.add_error('person', 'Member already in crew.')

                # Check overlap for existing S&F Requests and Mission
                overlapped_sfr, overlapped_missions = get_person_active_crews(
                    person=person,
                    arrival_date=start_date,
                    departure_date=end_date,
                    exclude_mission=self.mission,
                )
                if overlapped_sfr:
                    requests = ', '.join(get_sfr_html_urls(sfr_list=overlapped_sfr, open_new_tab=True))
                    form.add_error('person',
                                   f'Crew member already assigned to an overlapping S&F Request(s): {requests}')
                if overlapped_missions:
                    missions = ', '.join(get_mission_html_urls(missions_list=overlapped_missions, open_new_tab=True))
                    form.add_error('person', f'Crew member already assigned to an overlapping Mission(s) {missions}')

        cleaned_data = super(MissionCrewBaseFormSet, self).clean()

        if not people_to_save:
            raise forms.ValidationError('There must be at least one crew member assigned to this mission')

        if people_to_save:
            if not is_primary_contact_set:
                raise forms.ValidationError('Please select a primary mission contact')

        return cleaned_data


MissionCrewFormSet = modelformset_factory(
    MissionCrewPosition,
    extra=10,
    can_delete=True,
    form=MissionCrewPositionForm,
    formset=MissionCrewBaseFormSet,
    fields=['person', 'position', 'can_update_mission', 'is_primary_contact', 'legs', ]
)
