from django.db.models import Subquery, BooleanField, Case, When
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class AirCardPrefixManager(models.Manager):
    def with_state(self):
        most_recent_valid_from_qs = AirCardPrefix.objects.filter(
            valid_from__lte=timezone.now().date()
            ).order_by('-valid_from')[:1]
        
        qs = self.filter(valid_from__lte=timezone.now()).annotate(
            is_active=Case(
                When(valid_from=Subquery(most_recent_valid_from_qs.values('valid_from')), then=True),
                default=False,
                output_field=BooleanField()
            )
        )
        return qs

    def active(self):
        return self.with_state().filter(is_active=True)


class AirCardPrefix(models.Model):
    number_prefix = models.IntegerField(_("AIRcard Number Prefix"))
    valid_from = models.DateField(_("Valid From"),
                                  default=timezone.now,
                                  auto_now=False, auto_now_add=False)
    
    objects = AirCardPrefixManager()
    
    class Meta:
        db_table = 'aircard_prefixes'

    def __str__(self):
        return f'{self.number_prefix}'
