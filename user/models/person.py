from datetime import datetime, timedelta
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import pytz
from core.forms import phone_regex_validator
from core.utils.datatables_functions import get_colored_circle


class PersonTitle(models.Model):
    name = models.CharField(_("Title Name"), max_length=50)
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Organisation"),
                                     null=True, blank=True,
                                     related_name='people_titles',
                                     on_delete=models.CASCADE,
                                     )

    class Meta:
        db_table = 'people_titles'

    def __str__(self):
        return self.name


class PersonGender(models.Model):
    name = models.CharField(_("Name"), max_length=20)

    class Meta:
        db_table = 'people_genders'

    def __str__(self):
        return self.name


class PersonPronoun(models.Model):
    subject_pronoun = models.CharField(_("Subject Pronoun"), max_length=20)
    object_pronoun = models.CharField(_("Object Pronoun"), max_length=20)

    class Meta:
        ordering = ['id']
        db_table = 'people_personal_pronouns'

    def __str__(self):
        return self.subject_pronoun


class PersonTag(models.Model):
    person = models.ForeignKey("user.Person", on_delete=models.CASCADE)
    tag = models.ForeignKey("core.Tag", on_delete=models.CASCADE)

    class Meta:
        db_table = 'people_tags'

    def __str__(self):
        return f'{self.tag}'


class Person(models.Model):
    details = models.OneToOneField("user.PersonDetails",
                                   related_name='person_current',
                                   null=True,
                                   on_delete=models.CASCADE)
    ofac_api_id = models.CharField(_("OFAC API ID"), max_length=20,
                                   null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    aircraft_types = models.ManyToManyField("aircraft.AircraftType", blank=True,
                                            verbose_name=_("Person Aircraft Types"),
                                            through='PersonAircraftTypes')
    tags = models.ManyToManyField("core.Tag", through='user.PersonTag',
                                  blank=True, related_name='people')

    class Meta:
        db_table = 'people'

    def __str__(self):
        return f'{self.id}'

    def get_absolute_url(self):
        return reverse_lazy('admin:person', kwargs={'pk': self.pk})

    @property
    def main_organisation(self):
        first_dod_position = self.organisation_people.dod_positions().first()
        organisation = getattr(first_dod_position, 'organisation', None)
        return organisation

    @property
    def user_representation(self):
        return self.user.username

    @property
    def fullname(self):
        details = getattr(self, 'details', None)
        if details:
            fullname = f'{self.details.first_name}'
            if self.details.middle_name:
                fullname += f' {self.details.middle_name}'
            fullname += f' {self.details.last_name}'
            return fullname

    @property
    def initials(self):
        if not self.details:
            return '--'
        initials = self.details.first_name[:1] if self.details.first_name else '-'
        initials += self.details.last_name[:1] if self.details.last_name else '-'
        return initials

    @property
    def full_repr(self):
        result = ''
        if self.details:
            if self.details.title:
                result += f'{self.details.title.name} '
            result += self.details.first_name + ' ' + self.details.last_name

        return result

    @property
    def dod_positions(self):
        """
        Return person's positions only for DoD Operators (used in DoD Portal)
        :return: QuerySet
        """
        return self.organisation_people.dod_positions().cache()

    @property
    def primary_dod_position(self):
        """
        Return person's primary DoD position (used for mobile app API)
        :return: OrganisationPeople object (person position)
        """
        # TODO: Add application access permissions filter
        return self.organisation_people.dod_positions().first()

    @property
    def is_aml_staff(self):
        if hasattr(self, 'user'):
            return getattr(self.user, 'is_staff')
        return False

    @property
    def is_mil_team(self):
        if hasattr(self, 'user'):
            return self.user.roles.filter(pk=1000).cache(ops=['exists']).exists()
        return False

    @property
    def current_travel_document(self):
        return self.travel_documents.filter(type__is_td=True, is_current=True).last()

    @property
    def travel_document_status_light(self):
        travel_document = getattr(self, 'current_travel_document', None)
        if travel_document and travel_document.end_date > datetime.now().date():
            return get_colored_circle(color='green', tooltip_text='Travel document valid')
        elif travel_document and travel_document.end_date <= datetime.now().date():
            return get_colored_circle(color='orange', tooltip_text='Travel document expired')
        else:
            return get_colored_circle(color='red', tooltip_text='Travel document missing')

    @property
    def staff_name_representation(self):
        name = self.details.fullname
        team_name = ''
        team = self.teams.filter(is_primary_assignment=True)
        if team.exists():
            team_name = f' - {team[0].aml_team.name}'

        # == '' should be the only thing to check, as charfields shouldn't be NULL
        if self.details.abbreviated_name is None or self.details.abbreviated_name == '':
            return f'{name}{team_name}'
        return f'{name} ({self.details.abbreviated_name}){team_name}'


class PersonDetails(models.Model):
    person = models.ForeignKey("user.Person",
                               related_name='history',
                               on_delete=models.CASCADE)
    first_name = models.CharField(_("First Name"), max_length=50)
    middle_name = models.CharField(_("Middle Name"), max_length=50,
                                   null=True, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=50)
    abbreviated_name = models.CharField(_("Abbreviated Name"),
                                        null=True, blank=True,
                                        max_length=50)
    contact_email = models.EmailField(_("Personal Email"), max_length=254)
    contact_phone = models.CharField(_("Personal Phone"), max_length=128,
                                     null=True, blank=True,
                                     validators=[phone_regex_validator],
                                     )
    title = models.ForeignKey(PersonTitle, verbose_name=_("Title"),
                              null=True, blank=True,
                              on_delete=models.SET_NULL,
                              )
    personal_pronoun = models.ForeignKey("user.PersonPronoun",
                                         verbose_name=_("Personal Pronoun"),
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    change_effective_date = models.DateField(_("Change Effective Date"), auto_now=False, auto_now_add=True)

    class Meta:
        db_table = 'people_history'

    def __str__(self):
        return '{first_name} {last_name}'.format(
            first_name=self.first_name,
            last_name=self.last_name)

    def save(self, *args, **kwargs):
        self.pk = None
        super().save(*args, **kwargs)
        Person.objects.filter(pk=self.person.pk).update(details=self)

    @property
    def staff_name(self):
        if self.abbreviated_name:
            return self.abbreviated_name
        else:
            return self.fullname

    @property
    def fullname(self):
        result = f'{self.first_name} {self.last_name}'
        return result

    def complete_representation(self):
        person_details = self
        result = ''
        if person_details.title:
            result += f'{person_details.title.name} '

        result += f'{person_details.first_name} '

        if person_details.middle_name:
            result += f'{person_details.middle_name} '

        result += f'{person_details.last_name} '

        if person_details.personal_pronoun:
            personal_pronoun = person_details.personal_pronoun
            personal_pronoun_text = f'({personal_pronoun.subject_pronoun}/{personal_pronoun.object_pronoun})'
            result += f'{personal_pronoun_text} '

        return result

    @property
    def invitation_status(self):
        code = None
        text = None
        badge_bg = None

        # Check if the user's invitation is still pending
        user = self.person.user
        pending = user.is_invitation_sent and not user.password

        # Compare token sent date with token timeout (by default 72h)
        token_sent_cutoff = datetime.now().replace(tzinfo=pytz.utc) - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        expired = pending and (not user.last_token_sent_at or user.last_token_sent_at < token_sent_cutoff)

        if expired:
            code = 'expired'
            text = 'Invite Expired (Not accepted)'
            badge_bg = 'bg-danger'
        elif pending:
            code = 'pending'
            text = 'Invited (Not yet accepted)'
            badge_bg = 'bg-warning'

        status_vars = {
            'code': code,
            'text': text or '',
            'badge_bg': badge_bg,
        }
        return status_vars

    @property
    def operational_status(self):
        code = None
        text = None
        badge_bg = None
        text_color = None
        header_color = None

        # TODO: update sanctioned code
        if self.person.pk == 3:
            sanctioned = True
        else:
            sanctioned = None

        if sanctioned:
            code = 'sanctioned'
            text = 'Sanctioned'
            badge_bg = 'bg-danger'
            header_color = 'text-danger'
            text_color = ''

        status_vars = {
            'code': code,
            'text': text or '',
            'text_color': text_color,
            'badge_bg': badge_bg,
            'header_color': header_color,
        }
        return status_vars


class PersonAircraftTypes(models.Model):
    person = models.ForeignKey("user.Person", on_delete=models.CASCADE)
    aircraft = models.ForeignKey("aircraft.AircraftType", on_delete=models.CASCADE)

    class Meta:
        db_table = 'people_aircraft_types'


class PersonRole(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    code_name = models.CharField(_("Code Name"), max_length=3, unique=True)
    is_flight_crew = models.BooleanField(_("Flight Crew"), default=False)
    is_refueller = models.BooleanField(_("Refueller"), default=False)
    is_finance = models.BooleanField(_("Finance"), default=False)
    is_ops = models.BooleanField(_("OPS"), default=False)
    is_sales = models.BooleanField(_("Sales"), default=False)
    is_management = models.BooleanField(_("Management"), default=False)
    is_maintainer = models.BooleanField(_("Maintainer"), default=False)
    is_aircraft_owner = models.BooleanField(_("Aircraft Owner"), default=False)

    class Meta:
        ordering = ['name']
        db_table = 'people_roles'

    def __str__(self):
        return f'{self.name}'
