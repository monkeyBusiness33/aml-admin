from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.custom_form_fields import WeekdayField


class HandlingRequestRecurrence(models.Model):
    specific_recurrence_dates = models.CharField(_("Specific Dates"), max_length=1000, null=True, blank=True)
    operating_days = WeekdayField(_("Operating Days"), null=True, blank=True)
    final_recurrence_date = models.DateTimeField(_("Final Recurrence Date"), auto_now=False, auto_now_add=False,
                                                 null=True, blank=True)
    weeks_of_recurrence = models.IntegerField(_("Weeks of Recurrence"), validators=[MaxValueValidator(54,)],
                                              null=True, blank=True)
    handling_requests = models.ManyToManyField("handling.HandlingRequest",
                                               related_name='recurrence_groups',
                                               through='handling.HandlingRequestRecurrenceMission')

    class Meta:
        db_table = 'handling_requests_recurrences'
        app_label = 'handling'

    def get_handling_requests_sorted(self):
        return self.handling_requests.with_status().exclude(status__in=[4, 5, 7, 9, ]).order_by('arrival_date')

    def get_future_handling_requests(self):
        handling_requests = self.get_handling_requests_sorted()
        return handling_requests.filter(arrival_date__gt=timezone.now())


class HandlingRequestRecurrenceMission(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         related_name='recurrence_groups_membership',
                                         on_delete=models.CASCADE)
    recurrence = models.ForeignKey("handling.HandlingRequestRecurrence", verbose_name=_("Group"),
                                   related_name='handling_requests_membership',
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)

    class Meta:
        db_table = 'handling_requests_recurrences_missions'
        app_label = 'handling'
