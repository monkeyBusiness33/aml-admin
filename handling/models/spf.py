from django.db import models
from django.db.models import Case, When, Value, F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.storage_backends import SPFSignaturesStorage, AutoSPFDocumentsStorage, SPFDocumentsStorage


class ServiceProvisionForm(models.Model):
    handling_request = models.OneToOneField("handling.HandlingRequest", on_delete=models.CASCADE, related_name='spf')
    customer_comment = models.CharField(_("Comments"), max_length=255, null=True, blank=True)
    customer_signature = models.FileField(_("Customer Signature"),
                                          storage=SPFSignaturesStorage(),
                                          null=True)
    spf_document = models.FileField(_("SPF Document"),
                                    storage=SPFDocumentsStorage(), null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=False,
                                      default=timezone.now)

    class Meta:
        managed = True
        db_table = 'spf_submissions'
        app_label = 'handling'

    def __str__(self):
        return f'{self.id}'

    @property
    def dla_services_list(self):
        """Property returns list with all shared DLA services"""
        return self.services_taken.exclude(
            service__is_dla=True,
            service__custom_service_for_request__isnull=False
        ).order_by('service__name')

    @property
    def dla_taken_services_list(self):
        """Property returns list with taken shared DLA services"""
        return self.services_taken.filter(taken=True).exclude(
            service__is_dla=True,
            service__custom_service_for_request__isnull=False,
        ).order_by('service__name')

    @property
    def custom_services_list(self):
        """Property returns list with 6 items of taken services or None objects"""
        spf = self
        custom_services_max_count = 6
        services_taken = spf.services_taken.exclude(service__custom_service_for_request__isnull=True)[:6]

        absent_services = custom_services_max_count - services_taken.count()
        services_taken_list = list(services_taken)

        for i in range(absent_services):
            services_taken_list.append(None)

        return services_taken_list

    @property
    def custom_services_list_api(self):
        """Alternative property to get SPF custom services list only"""
        return self.services_taken.exclude(
            service__custom_service_for_request__isnull=True,
        ).order_by('service__name')[:6]


@receiver(post_save, sender=ServiceProvisionForm)
def add_mandatory_dla_services_to_spf(sender, instance, created, **kwargs): # noqa
    """Automatically add "Terminal Operations" and "Ramp Fee" DLA services"""
    if not hasattr(instance, 'skip_signal'):  # Debugging line to control signals count
        print('add_mandatory_dla_services_to_spf')
        from handling.models import HandlingService
        dla_services_to_add = HandlingService.objects.filter(
            is_active=True, is_dla=True, always_included=True,
            ).exclude(pk__in=instance.services_taken.all().values('service_id')).all()
        for dla_service in dla_services_to_add:
            instance.services_taken.create(
                service=dla_service,
                taken=True,
            )


class ServiceProvisionFormServiceTaken(models.Model):
    spf = models.ForeignKey("handling.ServiceProvisionForm", on_delete=models.CASCADE, related_name='services_taken')
    service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"), on_delete=models.PROTECT)
    taken = models.BooleanField(_("Taken"))

    class Meta:
        managed = True
        db_table = 'spf_service_taken'
        app_label = 'handling'

    def __str__(self):
        return f'{self.id}'


class AutoServiceProvisionForm(models.Model):
    handling_request = models.OneToOneField("handling.HandlingRequest",
                                            on_delete=models.CASCADE,
                                            related_name='auto_spf')
    spf_document = models.FileField(_("SPF Document"), storage=AutoSPFDocumentsStorage(), null=True)
    sent_to = models.ForeignKey("organisation.Organisation", verbose_name=_("Ground Handler"),
                                related_name='auto_spf_submissions',
                                null=True, blank=True,
                                on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=False, default=timezone.now)

    class Meta:
        managed = True
        db_table = 'spf_auto_submissions'
        app_label = 'handling'

    def __str__(self):
        return f'{self.id}'


class HandlingRequestSpf(models.Model):
    handling_request = models.OneToOneField("handling.HandlingRequest", verbose_name=_("S&F Request"),
                                            related_name='spf_v2',
                                            on_delete=models.CASCADE)
    is_reconciled = models.BooleanField(_("Is Reconciled"), default=False)
    reconciled_by = models.ForeignKey("user.Person", verbose_name=_("Reconciled By"),
                                      null=True, blank=True,
                                      related_name='reconciled_spf_v2',
                                      on_delete=models.CASCADE)
    reconciled_at = models.DateTimeField(_("Reconciled At"), auto_now=False, auto_now_add=False, null=True)

    class Meta:
        db_table = 'handling_requests_spf'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.handling_request.get_spf_v2_status.invalidate(self)


class HandlingRequestSpfServiceManager(models.Manager):
    def sorted(self):
        return self.annotate(
            name=Case(
                When(dla_service__isnull=False, then=F('dla_service__name')),
                When(handling_service__isnull=False, then=F('handling_service__name')),
                default=Value(''),
            )
        ).order_by('name')


class HandlingRequestSpfService(models.Model):
    spf = models.ForeignKey("HandlingRequestSpf", verbose_name=_("SPF"),
                            related_name='services',
                            on_delete=models.CASCADE)
    dla_service = models.ForeignKey("organisation.DlaService", verbose_name=_("DLA Service"),
                                    related_name='spf_v2_services',
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    handling_service = models.ForeignKey("handling.HandlingService", verbose_name=_("Handling Service"),
                                         related_name='spf_v2_services',
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    is_pre_ticked = models.BooleanField(_("Is Pre Ticked"), default=False)
    was_taken = models.BooleanField(_("Was Taken"), null=True)
    comments = models.CharField(_("Comments"), max_length=500, null=True)

    objects = HandlingRequestSpfServiceManager()

    class Meta:
        db_table = 'handling_requests_spf_services'
        constraints = [
            models.UniqueConstraint(fields=['spf', 'dla_service', ], name='unique_spf_service'),
        ]

    def __str__(self):
        return self.dla_service.name if self.dla_service else self.handling_service.name
