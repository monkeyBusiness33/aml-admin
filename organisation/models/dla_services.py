from django.db import models
from django.db.models import Q, OuterRef, Case, When
from django.utils.translation import gettext_lazy as _
from sql_util.aggregates import Exists, Subquery

from handling.utils.handling_services_utils import sync_dla_services_to_handling_services


class DlaServiceManager(models.Manager):
    dla_blanket_q = Q(is_always_selected=True, spf_services=None)
    dla_optional_q = Q(is_always_selected=False, spf_services=None)

    def active(self):
        return self.filter(is_deleted=False)

    def get_applicable_services(self, handler=None):
        """
        Return DLA services for the S&F Request auto-selecting
        :param handler:
        :return:
        """
        spf_services_sq = HandlerSpfService.objects.filter(dla_service_id=OuterRef('pk'), handler=handler)
        dla_services_is_always_selected_sq = DlaService.objects.filter(
            (Q(spf_services=None) | Q(spf_services__handler=handler)), pk__in=OuterRef('represents'))

        qs = self.active().prefetch_related(
            'spf_services',
        ).annotate(
            has_represented_service=Exists('represents'),
            has_applicable_rep=Exists('represents', filter=Q(spf_services__handler=handler)),
            is_aplicable=Case(
                When(spf_services__isnull=True, then=True),
                When(spf_services__handler=handler, then=True),
                When(has_represented_service=True, has_applicable_rep=True, then=True),
                default=False
            )
        ).filter(
            Q(is_aplicable=True) &
            (
                # Filter "directly represented services
                (Q(is_spf_included=True) & Q(spf_represented_by__isnull=True)) |
                # Filter Representatives of the included services
                (~Q(represents=None) & Q(represents__is_spf_included=True))
            )
        ).annotate(
            representats_is_always_selected=Subquery(
                dla_services_is_always_selected_sq.values('is_always_selected')[:1]),
            is_pre_ticked=Case(
                When(is_always_selected=True, then=True),
                When(representats_is_always_selected=True, then=True),
                default=False
            )
        ).annotate(
            is_handler_auto_select=Exists('spf_services', filter=Q(handler=handler)),
            applies_if_pax_onboard=Exists('spf_services', filter=Q(handler=handler, applies_if_pax_onboard=True)),
            applies_if_cargo_onboard=Exists('spf_services',
                                            filter=Q(handler=handler, applies_if_cargo_onboard=True)),
            applies_after_minutes=Subquery(spf_services_sq.filter(
                applies_after_minutes__isnull=False).values('applies_after_minutes')[:1]),
        ).distinct()
        return qs

    def get_for_handler_auto_select(self, handler):
        """
        Return DLA services which is available to assign to Handler as "Auto-Select" services.
        :param handler: Organisation
        :return: Queryset
        """
        qs = self.active().filter(
            ~Q(spf_services__handler=handler) | Q(spf_services=None),
            is_spf_included=True, is_always_selected=False,
        ).distinct()
        return qs


class DlaService(models.Model):
    name = models.CharField(_("Name"), max_length=200)
    codename = models.SlugField(_("Code Name"), max_length=25, null=True, blank=True, unique=True)
    khi_product_code = models.CharField(_("KHI Product Code"), max_length=200, null=True, blank=True)
    is_spf_included = models.BooleanField(_("Is Included in SPF?"), default=False)
    is_always_selected = models.BooleanField(_("Is Always Selected?"), default=False)
    is_deleted = models.BooleanField(_("Is Deleted?"), default=False)
    is_dla_visible_arrival = models.BooleanField(_("Visible for Arrival"), default=False)
    is_dla_visible_departure = models.BooleanField(_("Visible for Departure"), default=False)

    charge_services = models.ManyToManyField("pricing.ChargeService", verbose_name='Charge Services',
                                             blank=True,
                                             related_name='dla_services',
                                             through='organisation.DlaServiceMapping')
    spf_represented_by = models.ForeignKey("organisation.DlaService", verbose_name=_("Represented in SPF As"),
                                           related_name='represents',
                                           null=True, blank=True,
                                           on_delete=models.CASCADE)

    objects = DlaServiceManager()

    class Meta:
        db_table = 'organisations_dla_services'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        sync_dla_services_to_handling_services(self.pk)


class DlaServiceMapping(models.Model):
    charge_service = models.ForeignKey("pricing.ChargeService", verbose_name=_("Charge Service"),
                                       related_name='dla_service_mappings',
                                       on_delete=models.CASCADE)
    dla_service = models.ForeignKey("DlaService", verbose_name=_("DLA Service"),
                                    related_name='dla_service_mappings',
                                    on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_dla_services_mapping'


class HandlerSpfService(models.Model):
    handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Ground Handler"),
                                related_name='spf_services',
                                null=True, blank=True,
                                on_delete=models.CASCADE)
    dla_service = models.ForeignKey("DlaService", verbose_name=_("DLA Service"),
                                    related_name='spf_services',
                                    on_delete=models.CASCADE)
    applies_after_minutes = models.IntegerField(_("Applies After Minutes"), null=True, blank=True)
    applies_if_pax_onboard = models.BooleanField(_("Applies if Pax Onboard"), default=False)
    applies_if_cargo_onboard = models.BooleanField(_("Applies if Cargo Onboard"), default=False)
    source_supplier_invoice_ref = models.CharField(_("Source Supplier Invoice Ref"), max_length=200,
                                                   null=True, blank=True)
    source_supplier_pld_ref = models.CharField(_("Source Supplier PLD Red"), max_length=200,
                                               null=True, blank=True)
    source_aml_order_ref = models.CharField(_("Source AML Order Ref"), max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'organisations_handlers_spf_services'
