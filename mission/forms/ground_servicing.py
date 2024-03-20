import random

from django import forms
from django.db.models import Q, Subquery, OuterRef
from django.forms import widgets, BaseModelFormSet, modelformset_factory, BaseFormSet, formset_factory

from handling.form_widgets import PersonCrewDependentPickWidget, CrewMemberPositionPickWidget, HandlingServicePickWidget
from handling.models import HandlingService
from mission.models import MissionCrewPosition, MissionTurnaroundService, MissionTurnaround
from user.models import Person


class MissionLegServicingServiceForm(forms.Form):
    arr = forms.BooleanField(
        label='A',
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input m-0',
        })
    )
    dep = forms.BooleanField(
        label='D',
        required=False,
        widget=widgets.CheckboxInput(attrs={
            'class': 'form-check-input m-0',
        })
    )
    qty = forms.IntegerField(
        label='Qty',
        required=False,
        widget=widgets.NumberInput(attrs={
            'class': 'form-control qty-input',
        })
    )
    #
    # note = forms.CharField(
    #     label='Desc',
    #     required=False,
    #     widget=widgets.HiddenInput(attrs={
    #     })
    # )
    # class Meta:
    #     model = MissionLegServicingService
    #     fields = ['on_arrival', 'on_departure', ]
    #     widgets = {
    #         "on_arrival": widgets.CheckboxInput(attrs={
    #             'class': 'form-check-input',
    #         }),
    #         "on_departure": widgets.CheckboxInput(attrs={
    #             'class': 'form-check-input',
    #         }),
    #     }


class MissionGroundServicingServiceForm(forms.Form):
    service = forms.ModelChoiceField(
        queryset=HandlingService.objects.all(),
        label='Service',
        required=True,
        widget=HandlingServicePickWidget(
            attrs={
                'class': 'form-control',
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        super().__init__(*args, **kwargs)
        service = self.initial.get('service')
        print('service', service)

        qs = MissionTurnaroundService.objects.filter(
            turnaround__mission_leg__mission=self.mission,
            service_id=service,
        ).order_by('turnaround__mission_leg__sequence_id')

        print('qs', qs)

        sq = MissionTurnaroundService.objects.filter(turnaround=OuterRef('pk'), service=service)

        qs = MissionTurnaround.objects.filter(
            mission_leg__mission=self.mission,
        ).annotate(
            arr=Subquery(sq.values('on_arrival')[:1]),
            dep=Subquery(sq.values('on_departure')[:1]),
        ).values('arr', 'dep')

        leg_formset = formset_factory(form=MissionLegServicingServiceForm, extra=0)
        self.leg_formset = leg_formset(initial=qs, prefix=service)

    def is_valid(self):
        is_valid = super().is_valid()
        for field in self.errors:
            if field != '__all__':
                self.fields[field].widget.attrs['class'] = 'form-control is-invalid'
        return is_valid


class MissionGroundServicingServiceBaseFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.mission = kwargs.pop('mission', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # organisation = getattr(self.mission, 'organisation')
        # if self.mission:
        #     self.queryset = MissionCrewPosition.objects.filter(
        #         mission=self.mission).all()
        # else:
        #     self.queryset = MissionCrewPosition.objects.none()
        #
        # for form in self.forms:
        #     form.fields['person'].queryset = Person.objects.filter(organisations=organisation)
        #
        #     form.instance.mission = self.mission
        #     if form.instance.is_primary_contact:
        #         form.initial['can_update_mission'] = True
        #         form.instance.can_update_mission = True

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['mission'] = self.mission
        return kwargs

    # def clean(self):
    #     forms_to_delete = self.deleted_forms
    #     valid_forms = [
    #         form
    #         for form in self.forms
    #         if form.is_valid() and form not in forms_to_delete
    #     ]
    #     # Get id's for every instance selected to delete to exclude it in duplicate check
    #     instance_pks_to_delete = [form.instance.pk for form in forms_to_delete]
    #     people_to_save = []
    #     is_primary_contact_set = False
    #
    #     # Set deleting user for activity_log record
    #     for form_to_delete in forms_to_delete:
    #         form_to_delete.instance.updated_by = self.request.user.person
    #
    #     for form in valid_forms:
    #         person = getattr(form.instance, 'person', None)
    #         form.instance.updated_by = self.request.user.person
    #         is_primary_contact = getattr(form.instance, 'is_primary_contact', False)
    #
    #         if form.instance.pk not in instance_pks_to_delete and person:
    #             # Create list of people to save for future validation
    #             people_to_save.append(person)
    #             # Trace is at least one person has set as primary contact
    #             if is_primary_contact:
    #                 is_primary_contact_set = True
    #
    #         if person:
    #             # Exclude existing instance from duplicate checking versus self
    #             if form.instance.pk:
    #                 exclude_self_q = ~Q(pk=form.instance.pk)
    #             else:
    #                 exclude_self_q = ~Q()
    #
    #             exclude_instances_to_delete_q = ~Q(pk__in=instance_pks_to_delete)
    #             crew_member = MissionCrewPosition.objects.filter(exclude_self_q, exclude_instances_to_delete_q,
    #                                                              mission=self.mission,
    #                                                              person=person)
    #             if crew_member.exists():
    #                 form.add_error('person', 'Member already in crew.')
    #
    #     cleaned_data = super(MissionCrewBaseFormSet, self).clean()
    #
    #     if not people_to_save:
    #         raise forms.ValidationError('There must be at least one crew member assigned to this mission')
    #
    #     if people_to_save:
    #         if not is_primary_contact_set:
    #             raise forms.ValidationError('Please select a primary mission contact')
    #
    #     return cleaned_data



