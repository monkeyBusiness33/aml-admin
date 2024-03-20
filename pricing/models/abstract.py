from django.db import models
from django.utils.translation import gettext_lazy as _


class PrioritizedModel(models.Model):
    PRIORITY_CHOICES = [
        (3, "Low"),
        (2, "Medium"),
        (1, "High"),
        (0, "Urgent"),
    ]

    priority = models.PositiveSmallIntegerField(_("Priority"), choices=PRIORITY_CHOICES,
                                                default=2)

    class Meta:
        abstract = True
