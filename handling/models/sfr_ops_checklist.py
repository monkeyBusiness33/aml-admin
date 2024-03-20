from django.db import models
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _


class SfrOpsChecklistParameterQuerySet(models.QuerySet):
    def with_details(self):
        return self.annotate(
            location_str=Concat(
                F('location__details__registered_name'),
                Value(' ('),
                Case(
                    When(Q(location__airport_details__iata_code__isnull=True)
                         | Q(location__airport_details__iata_code=''), then=F(
                        'location__airport_details__icao_code')),
                    When(Q(location__airport_details__icao_code__isnull=True)
                         | Q(location__airport_details__icao_code=''), then=F(
                        'location__airport_details__iata_code')),
                    default=Concat(
                        'location__airport_details__icao_code',
                        Value(' / '),
                        'location__airport_details__iata_code',
                        output_field=CharField()
                    ),
                    output_field=CharField()
                ),
                Value(')')
            ))


class SfrOpsChecklistParameter(models.Model):
    location = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                 related_name="location_specific_sfr_ops_checklist_parameters",
                                 on_delete=models.CASCADE, null=True, blank=True,
                                 limit_choices_to={"details__type_id": 8, "airport_details__isnull": False})
    category = models.ForeignKey("SfrOpsChecklistCategory", verbose_name=_("Category"),
                                 related_name="parameters", on_delete=models.CASCADE, )
    description = models.CharField(_("Description"), max_length=500, null=True, blank=True)
    url = models.URLField(_("URL"), max_length=500, null=True, blank=True)
    is_active = models.BooleanField(_("Is Active?"), default=True)

    objects = SfrOpsChecklistParameterQuerySet.as_manager()

    class Meta:
        db_table = "aml_sfr_ops_checklist_parameters"
        ordering = ['category', 'description', 'url']


class SfrOpsChecklistCategory(models.Model):
    name = models.CharField(_("Name"), max_length=100)

    class Meta:
        db_table = "aml_sfr_ops_checklist_categories"
        ordering = ['name']


class HandlingRequestOpsChecklistItem(models.Model):
    request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                related_name="sfr_ops_checklist_items", on_delete=models.CASCADE)
    checklist_item = models.ForeignKey("handling.SfrOpsChecklistParameter", verbose_name=_("Checklist Item"),
                                       related_name="checklist_item_instances", on_delete=models.CASCADE)
    is_completed = models.BooleanField(_("Is Completed?"), default=False)
    completed_at = models.DateTimeField(_("Completed At"), null=True)
    completed_by = models.ForeignKey("user.Person", verbose_name=_("Completed By"),
                                     related_name="completed_sfr_ops_checklist_items",
                                     on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "handling_requests_ops_checklist"
        ordering = ['is_completed', 'checklist_item']

    def __str__(self):
        item = self.checklist_item

        return f'{item.category.name} - {item.description or item.url}'
