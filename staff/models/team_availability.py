from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

# Common fields
class CalendarFields(models.Model):
    start_hour = models.TimeField(_("Start Time"))
    end_hour = models.TimeField(_("End Time"))
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    entry_type = models.ForeignKey('staff.EntryType', verbose_name=_("Entry Type"),
                                   on_delete=models.CASCADE)
    comment = models.CharField(_("Comment"), max_length=500, blank=True, default='')

    class Meta:
        abstract = True


class LogFields(models.Model):
    created_on = models.DateTimeField(_("Created On"), blank=True)
    updated_on = models.DateTimeField(_("Updated On"), null=True, blank=True)
    updated_by = models.ForeignKey('user.Person', verbose_name=_("Updated By"),
                                  on_delete=models.CASCADE, null=True, blank=True, related_name="+")

    class Meta:
        abstract = True


class TrackingFields(models.Model):
    is_approved = models.BooleanField(_("Approved?"), default=False)
    is_disapproved = models.BooleanField(_("Disapproved?"), default=False)
    flagged_for_delete = models.BooleanField(_("Deleted?"), default=False)
    flagged_for_edit = models.BooleanField(_("Edited?"), default=False)
    original_entry = models.ForeignKey('self', verbose_name=_("Edited Entry"),
                                       on_delete=models.SET_NULL, null=True, blank=True)
    action_on = models.DateTimeField(_("Action On"), null=True, blank=True)

    class Meta:
        abstract = True

# Simple Entry - specify dates instead of days
# Overrides Blanket Entry and Blanket Entry Override on collision
class SpecificEntry(CalendarFields, LogFields, TrackingFields):
    person = models.ForeignKey('user.Person', verbose_name=_("Person"),
                               on_delete=models.CASCADE,
                               related_name='specific_entries')
    action_by = models.ForeignKey('user.Person', verbose_name=_("Actioned By"),
                                  on_delete=models.CASCADE, blank=True, null=True,
                                  related_name="actioned_specific_entries")
    created_by = models.ForeignKey('user.Person', verbose_name=_("Created By"),
                                   on_delete=models.CASCADE, blank=True,
                                   related_name="created_specific_entries")
    applied_on_dates = \
        ArrayField(models.PositiveSmallIntegerField(_("Dates"),
                  validators=[MinValueValidator(1), MaxValueValidator(31)]))
    team = models.ForeignKey('organisation.OrganisationAMLTeam', verbose_name=_("Team"),
                             on_delete=models.CASCADE, related_name='team_specific_entries')
    replaces_other_entry = models.ForeignKey('staff.BlanketEntry', verbose_name=_("Replaces Other Entry"),
                             on_delete=models.SET_NULL, blank=True, null=True, related_name='replaces_other_entry')
    replaces_own_entry = models.ForeignKey('staff.BlanketEntry', verbose_name=_("Replaces Own Entry"),
                             on_delete=models.SET_NULL, blank=True, null=True, related_name='replaces_own_entry')

    class Meta:
        db_table = 'staff_specific_entry'


# Ideally only a few entries that cover a whole year (Person A always works on weekends [week 1])
# Applied on Weeks: from start_date how many weeks we should apply this entry for (depending on periodicity)
class BlanketEntry(CalendarFields, LogFields, TrackingFields):
    person = models.ForeignKey('user.Person', verbose_name=_("Person"),
                               on_delete=models.CASCADE, related_name='blanket_entries')
    action_by = models.ForeignKey('user.Person', verbose_name=_("Action By"),
                                  on_delete=models.CASCADE, blank=True, null=True,
                                  related_name="actioned_blanket_entries")
    created_by = models.ForeignKey('user.Person', verbose_name=_("Created By"),
                                   on_delete=models.CASCADE, blank=True,
                                   related_name="created_blanket_entries")
    applied_on_days = \
        ArrayField(models.PositiveSmallIntegerField(_("Days"), default=[1,2,3,4,5],
                                                    validators=[MinValueValidator(1), MaxValueValidator(7)]))
    applied_on_weeks = \
        ArrayField(models.PositiveSmallIntegerField(_("Applied on Weeks"), blank=True, null=True,
                                                    validators=[MinValueValidator(0), MaxValueValidator(53)]))
    team = models.ForeignKey('organisation.OrganisationAMLTeam', verbose_name=_("Team"),
                             on_delete=models.CASCADE, related_name='team_blanket_entries')

    class Meta:
        db_table = 'staff_blanket_entry'


class EntryType(models.Model):
    name = models.CharField(_('Name'), max_length=20)
    requires_full_workday = models.BooleanField(_('Requires Full Workday?'), default=False)
    requires_comment = models.BooleanField(_('Requires Comment?'), default=False)
    is_specific_only = models.BooleanField(_('Specific Entry Only?'), default=False)
    background = models.CharField(_('Background'), max_length=7, default='#515d8a')

    class Meta:
        db_table = 'staff_entry_types'


class FinalizedMonth(models.Model):
    year = models.SmallIntegerField(_('Year'), validators=[MinValueValidator(2000), MaxValueValidator(3000)])
    month = models.SmallIntegerField(_('Month'), validators=[MinValueValidator(1), MaxValueValidator(12)])
    closed_on = models.DateTimeField(_('Closed On'), auto_now_add=True)
    closed_by = models.ForeignKey('user.Person', verbose_name=_("Closed By"),
                                  on_delete=models.CASCADE, related_name='finalized_months')

    class Meta:
        db_table = 'staff_finalized_month'


class TeamRole(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'staff_team_roles'

    def __str__(self):
        return self.name

