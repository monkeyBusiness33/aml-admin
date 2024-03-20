from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ActivityLog(models.Model):
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=False, default=timezone.now)
    author = models.ForeignKey("user.Person", verbose_name=_("Author"),
                               null=True,
                               related_name='authored_activity_log_records',
                               on_delete=models.SET_NULL)
    author_text = models.CharField(_("Author (raw)"), max_length=50, null=True)
    record_slug = models.SlugField(_("Record Slug"), null=True, max_length=150)

    value_name = models.CharField(_("Entity/Field Name"), max_length=150, null=True)
    value_prev = models.CharField(_("Previous Value"), max_length=500, null=True)
    value_new = models.CharField(_("New Value"), max_length=500, null=True)
    details = models.CharField(_("Details"), max_length=1000, null=True)
    data = models.JSONField(null=True)

    # Entities
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Organisation"),
                                     related_name='activity_log',
                                     null=True,
                                     on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='activity_log',
                               null=True,
                               on_delete=models.CASCADE)
    aircraft = models.ForeignKey("aircraft.Aircraft", verbose_name=_("Aircraft"),
                                 null=True,
                                 related_name='activity_log',
                                 on_delete=models.CASCADE)
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                null=True,
                                related_name='activity_log',
                                on_delete=models.CASCADE)
    mission_leg = models.ForeignKey("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                    null=True,
                                    related_name='activity_log',
                                    on_delete=models.CASCADE)
    mission_turnaround = models.ForeignKey("mission.MissionTurnaround", verbose_name=_("Mission Turnaround"),
                                           null=True,
                                           related_name='activity_log',
                                           on_delete=models.CASCADE)
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("S&F Request"),
                                         null=True,
                                         related_name='activity_log',
                                         on_delete=models.CASCADE)
    handling_request_movement = models.ForeignKey("handling.HandlingRequestMovement", verbose_name=_("Movement"),
                                                  null=True,
                                                  related_name='activity_log',
                                                  on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']
        db_table = 'activity_log'

    NULL_AUTHOR_DEFAULTS_TO_AUTO_SLUGS = ['sfr_movement_service_added']

    def __str__(self):
        return f'{self.pk}'

    def get_created_at_display(self):
        return self.created_at.strftime("%Y-%m-%d %H:%M")

    def get_author_display(self):
        if self.author:
            return self.author.fullname
        elif self.author_text:
            return self.author_text
        elif self.record_slug in self.NULL_AUTHOR_DEFAULTS_TO_AUTO_SLUGS:
            return 'Automatic Update'
        else:
            return ''

    def get_details_display(self):
        text = ''

        # Custom formatting for Mission related records
        if self.mission_leg_id and not self.mission_id:
            if self.mission_leg.is_cancelled:
                text += '<del>'
            text += f'<i>Flight Leg {self.mission_leg.sequence_id}:</i> '

        # Custom formatting for Mission Turnaround rows
        if self.mission_turnaround_id and not self.mission_id:
            if self.mission_turnaround.mission_leg.is_cancelled:
                text += '<del>'
            text += f'<i>{self.mission_turnaround.full_repr}:</i> '

        # Custom formatting for S&F Request Movement related records
        if self.handling_request_movement_id and not self.handling_request_id:
            text += f'<i>{self.handling_request_movement.direction_name} Movement:</i> '

        # Custom formatting by 'record_slug'
        if self.record_slug == 'mission_assigned_mil_team_member_id_amendment':
            return f'Assigned Mil Team Member {self.value_prev} re-assigned to {self.value_new}'

        if self.record_slug == 'mission_leg_cancellation':
            return f'Cancelled Flight Leg - {self.mission_leg.sequence_id} {self.mission_leg}'

        if self.record_slug == 'sfr_callsign_amendment_confirmation':
            return self.details

        if self.record_slug == 'sfr_movement_service_added':
            text += f'{self.details} service has been added'
            return text
        if self.record_slug == 'sfr_movement_service_removed':
            text += f'{self.details} service has been removed'
            return text

        if self.record_slug == 'mission_turnaround_service_added':
            text += f'{self.details} service has been added'
            return text
        if self.record_slug == 'mission_turnaround_service_delete':
            text += f'{self.details} service has been removed'
            return text

        if self.record_slug == 'sfr_ops_checklist_item_status_change':
            category = self.data['category']
            url = self.data['url']
            description = self.data['description'] or url

            if url:
                description = f'<a href="{url}">{description}</a>'

            if int(self.value_new):
                return f'Checklist item marked as done: {category} / {description}'
            else:
                return f'Checklist item marked as outstanding: {category} / {description}'

        # Generic formatting
        if self.value_prev or self.value_new:
            text += f'{self.value_name} {self.value_prev} amended to {self.value_new}'
        else:
            text += self.details or ''

        if self.mission_leg_id and self.mission_leg.is_cancelled:
            text += '</del>'

        if self.mission_turnaround_id and self.mission_turnaround.mission_leg.is_cancelled:
            text += '</del>'

        return text
