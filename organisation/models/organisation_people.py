from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.forms import phone_regex_validator
from core.utils.datatables_functions import get_datatable_badge


def _organisation_people_create_history_record(instance, is_deleting=False):
    """
    Function to create OrganisationPeopleHistory records on the
    OrganisationPeople saving and deletion.
    :param instance: OrganisationPeople instance
    :param is_deleting: boolean
    :return:
    """
    from django.apps import apps as django_apps
    organisation_people_cls = django_apps.get_model(
        'organisation.OrganisationPeople')
    organisation_people_history_cls = django_apps.get_model(
        'organisation.OrganisationPeopleHistory')

    previous_state = organisation_people_cls.objects.get(pk=instance.pk)
    if any([
        previous_state.job_title != instance.job_title,
        previous_state.role != instance.role,
        is_deleting
    ]):
        organisation_people_history_cls.objects.create(
            person=previous_state.person,
            organisation=previous_state.organisation,
            role=previous_state.role,
            is_decision_maker=previous_state.is_decision_maker,
            is_authorising_person=previous_state.is_authorising_person,
            job_title=previous_state.job_title,
            start_date=previous_state.start_date,
        )


class OrganisationPeopleManager(models.Manager):
    def dod_positions(self):
        """
        Positions with Organisation whom can be serviced as DoD
        :return: QuerySet
        """
        return self.filter(organisation__operator_details__isnull=False,
                           organisation__operator_details__type_id__in=[13, 14, 15, 16, 17],
                           )


class OrganisationPeople(models.Model):
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='organisation_people',
                               on_delete=models.CASCADE)
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Organisation Name"),
                                     related_name='organisation_people',
                                     on_delete=models.CASCADE)
    role = models.ForeignKey("user.PersonRole",
                             verbose_name=_("Job Role"), on_delete=models.CASCADE)
    contact_email = models.EmailField(_("Direct Email"), max_length=254)
    contact_phone = models.CharField(_("Direct Phone"), max_length=128,
                                     null=True, blank=True,
                                     validators=[phone_regex_validator],
                                     )
    is_decision_maker = models.BooleanField(_("Is Decision Maker?"), default=False)
    is_authorising_person = models.BooleanField(_("Is Authorising Person?"), default=False)
    job_title = models.CharField(_("Job Title"), max_length=50)
    start_date = models.DateField(_("Starting Date"), blank=True,
                                  auto_now=False, auto_now_add=False)
    applications_access = models.ManyToManyField("core.AmlApplication",
                                                 verbose_name=_("Applications Access"),
                                                 through='organisation.OrganisationPersonPositionApplication',
                                                 blank=True, related_name='organisation_people')
    aircraft_types = models.ManyToManyField("aircraft.AircraftType",
                                            verbose_name=_("Aircraft Types"),
                                            through='organisation.OrganisationPersonPositionAircraftType',
                                            blank=True, related_name='organisation_people')
    primary_region = models.ForeignKey("core.Region",
                                       verbose_name=_("Primary Region"),
                                       related_name="organisation_people",
                                       on_delete=models.SET_NULL, blank=True, null=True)

    objects = OrganisationPeopleManager()

    class Meta:
        db_table = 'organisations_people'

    def __str__(self):
        return f'{self.role}'

    def save(self, *args, **kwargs):
        if not self.start_date:
            self.start_date = timezone.now()
        if self.pk:
            _organisation_people_create_history_record(instance=self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        _organisation_people_create_history_record(instance=self, is_deleting=True)
        super().delete(*args, **kwargs)

    def get_sfr_list(self, managed: bool = False, owned: bool = False):
        """
        Return position related S&F Requests
        :param managed: Return only S&F Requests which can be updated by person, ignored if "DoD Planners" access level
        assigned to the person.
        :param owned: Return only S&F which person are 'is_primary_contact: True' for
        :return: HandlingRequest QuerySet
        """
        qs = self.organisation.handling_requests.all()

        is_dod_planners = self.applications_access.filter(code='dod_planners').exists()
        if is_dod_planners:
            return qs
        else:
            qs = qs.filter(mission_crew__person=self.person)

        if owned:
            qs = qs.filter(Q(mission_crew__person=self.person) & Q(mission_crew__is_primary_contact=True))
            return qs

        if managed and not is_dod_planners:
            qs = qs.filter(
                Q(mission_crew__person=self.person),
                (Q(mission_crew__is_primary_contact=True) | Q(mission_crew__can_update_mission=True))
            )

        return qs.distinct()

    @property
    def managed_sfr_list(self):
        """
        Return  S&F Requests which person able to update
        :return: HandlingRequest QuerySet
        """
        qs = self.get_sfr_list(managed=True)
        return qs

    @property
    def owned_sfr_list(self):
        """
        Return person's owned S&F Requests
        :return: HandlingRequest QuerySet
        """
        qs = self.get_sfr_list(owned=True)
        return qs

    def get_missions_list(self, managed: bool = False):
        """
        Returns missions available for current position
        :return:
        """
        qs = self.organisation.missions.all()
        return qs

    @property
    def managed_missions_list(self):
        return self.get_missions_list(managed=True)

    @property
    def repr_for_recipients_list(self):
        email_badge_str = get_datatable_badge(
            badge_text='CC:',
            badge_class='bg-gray-400 badge-multiline badge-250 pt-1',
            tooltip_text=f"Use email in 'CC:' field",
            tooltip_placement='top'
        )

        return (f'{self.person.fullname}'
                f' <i class="text-gray-400">({self.job_title})</i>'
                f'<br>{email_badge_str}{self.contact_email}')


class OrganisationPeopleHistory(models.Model):
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='organisation_people_history',
                               on_delete=models.CASCADE)
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Organisation"),
                                     on_delete=models.CASCADE)
    role = models.ForeignKey("user.PersonRole",
                             verbose_name=_("Role"), on_delete=models.CASCADE)
    is_decision_maker = models.BooleanField(_("Is Decision Maker?"), default=False)
    is_authorising_person = models.BooleanField(_("Is Authorising Person?"), default=False)
    job_title = models.CharField(_("Job Title"), max_length=50)
    start_date = models.DateField(_("Starting Date"), auto_now=False, auto_now_add=False)
    end_date = models.DateField(_("End Date"), auto_now=False, auto_now_add=True)

    class Meta:
        db_table = 'organisations_people_history'

    def __str__(self):
        return f'{self.job_title} at {self.organisation.details.registered_name}'


class OrganisationPersonPositionApplication(models.Model):
    position = models.ForeignKey("organisation.OrganisationPeople", verbose_name=_("Position"),
                                 related_name='position_applications',
                                 on_delete=models.CASCADE)
    application = models.ForeignKey("core.AmlApplication",
                                    verbose_name=_("Application"),
                                    on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_people_applications'

    def __str__(self):
        return f'{self.application}'


class OrganisationPersonPositionAircraftType(models.Model):
    position = models.ForeignKey("organisation.OrganisationPeople", verbose_name=_("Position"),
                                 related_name='position_aircraft_types',
                                 on_delete=models.CASCADE)
    aircraft_type = models.ForeignKey("aircraft.AircraftType",
                                      verbose_name=_("Aircraft Type"),
                                      on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_people_aircraft_types'

    def __str__(self):
        return f'{self.aircraft_type}'


class OrganisationAMLTeam(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'organisations_aml_teams'

    def __str__(self):
        return f'{self.name}'


# One person - Multiple teams,
class OrganisationPersonTeam(models.Model):
    person = models.ForeignKey('user.Person', verbose_name=_('Person'),
                                  related_name="teams",
                                  on_delete=models.CASCADE)
    manages_own_schedule = models.BooleanField(default=False)
    # deadline_applicable = models.ForeignKey('staff.Deadline', verbose_name=_('Deadline'),
    #                                         related_name='related_deadlines',
    #                                         on_delete=models.SET_NULL, blank=True, null=True) # Not priority yet, TBC
    aml_team = models.ForeignKey('OrganisationAMLTeam',
                                 verbose_name = _('AML Team'),
                                 related_name = 'people_in_team',
                                 on_delete=models.CASCADE)
    is_primary_assignment = models.BooleanField(default=False)
    role = models.ForeignKey('staff.TeamRole',
                             verbose_name = _('Role'),
                             related_name = '+',
                             on_delete=models.SET_NULL, null=True) # Can be temporarily unassigned

    class Meta:
        db_table = 'organisations_people_teams'

    def __str__(self):
        return f'{self.person.fullname} ({self.aml_team})'
