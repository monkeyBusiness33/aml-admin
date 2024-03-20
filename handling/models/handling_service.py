from django.core.cache import cache
from django.db import models
from django.db.models import Q, F, Count, IntegerField, BooleanField, Case, When, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class HandlingServiceManager(models.Manager):
    def active(self):
        return self.filter(is_active=True, deleted_at__isnull=True)

    def regular_services(self, movement_direction, airport, handling_request):
        return self.filter(deleted_at__isnull=True).filter(
            # Regular airport-based services
            Q(is_active=True, is_dla=False,
              hs_availability__direction=movement_direction,
              hs_availability__airport=airport,
              organisations=None,
              custom_service_for_request__isnull=True) |
            # Organisation services
            Q(is_active=True,
              is_dla=False,
              organisations=handling_request.customer_organisation,
              custom_service_for_request__isnull=True)
        )

    def dod_services(self, movement_direction, airport, handling_request):
        """Returns services for DoD clients

        Args:
            movement_direction (obj): Movement direction for HandlingService availability filter
            airport (obj): Airport object for HandlingService availability filter
            handling_request (obj): HandlingRequest object for custom services filtering

        Returns:
            QuerySet: Will contains regular services for given location & direction and custom ones
            for HandlingRequest object along with shared DLA services
        """
        dla_movement_visibility = {}
        handler = handling_request.handling_agent

        spf_version = 1 if handling_request.is_legacy_spf_v1 else 2

        if spf_version == 1:
            is_dla_service_q = Q(is_dla=True)
            dla_applicability_q = Q()
            optional_service_q = (Q(is_dla=False) & Q(is_dla_v2=False))
            if movement_direction.code == 'ARRIVAL':
                dla_movement_visibility = {'is_dla_visible_arrival': True}
            if movement_direction.code == 'DEPARTURE':
                dla_movement_visibility = {'is_dla_visible_departure': True}
        else:
            is_dla_service_q = Q(is_dla_v2=True, dla_service__isnull=False, dla_service__is_always_selected=False)
            dla_applicability_q = (Q(dla_service__spf_services=None) | Q(dla_service__spf_services__handler=handler))
            optional_service_q = ((Q(is_dla=False) & Q(is_dla_v2=False)) | Q(is_spf_v2_non_dla=True))
            if movement_direction.code == 'ARRIVAL':
                dla_movement_visibility = {'is_dla_v2_visible_arrival': True}
            if movement_direction.code == 'DEPARTURE':
                dla_movement_visibility = {'is_dla_v2_visible_departure': True}

        return self.active().annotate(
            spf_version=Value(spf_version),
        ).filter(
            # Regular airport-based services
            Q(
                (
                    (Q(hs_availability__direction=movement_direction) & Q(hs_availability__airport=airport)) |
                    Q(hs_availability=None)
                ),
                optional_service_q,
                organisations=None,
                custom_service_for_request__isnull=True,
            ) |
            # Organisation services
            Q(
                optional_service_q,
                organisations=handling_request.customer_organisation,
                custom_service_for_request__isnull=True,
            ) |
            # Custom services for given HandlingRequest
            Q(custom_service_for_request=handling_request) |
            # DLA services
            Q(
                Q(is_dla_service_q),
                dla_applicability_q,
                **dla_movement_visibility,
                custom_service_for_request__isnull=True,
            )
        ).distinct()

    def dod_all(self, organisation):
        """Returns all DoD Handling Services

        Returns:
            QuerySet: HandlingServices list
        """
        return self.active().annotate(
            spf_version=Value(2),
        ).filter(
            Q(organisations__isnull=True) | Q(organisations=organisation),
            # Exclude DLAv1 services
            # ~Q(is_dla=True, is_dla_v2=True, is_spf_v2_non_dla=False),
            always_included=False,
            custom_service_for_request__isnull=True,
        )


class HandlingService(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    codename = models.SlugField(_("Code Name"), max_length=25,
                                null=True, blank=True,
                                db_index=True, unique=True)
    is_active = models.BooleanField(_("Active"), default=True)
    is_allowed_free_text = models.BooleanField(_("Allow Free Text Entry?"), default=False)
    is_allowed_quantity_selection = models.BooleanField(_("Allow Quantity Selection?"),
                                                        default=False)
    quantity_selection_uom = models.ForeignKey("core.UnitOfMeasurement",
                                               verbose_name=_("Unit of Measure"),
                                               limit_choices_to={'is_fluid_uom': True},
                                               null=True, blank=True,
                                               on_delete=models.CASCADE)

    # SPFv1
    is_dla = models.BooleanField(_("Always Display in Services Lists?"), db_index=True,
                                 help_text="Once been enabled - all airports settings will be cleared", default=False)
    is_dla_visible_arrival = models.BooleanField(_("Visible for Arrival"),
                                                 default=False, db_index=True,)
    is_dla_visible_departure = models.BooleanField(_("Visible for Departure"),
                                                   default=False, db_index=True,)
    is_spf_visible = models.BooleanField(_("SPF Form Visible"), default=False, db_index=True)

    # SPFv2
    is_dla_v2 = models.BooleanField(_("Is DLAv2 Service?"), default=False)
    is_dla_v2_visible_arrival = models.BooleanField(_("SPFv2: Visible for Arrival"),  default=False)
    is_dla_v2_visible_departure = models.BooleanField(_("SPFv2: Visible for Departure"), default=False)
    is_spf_v2_non_dla = models.BooleanField(_("SPFv2: Optional Service (Overrides is_dla)"), default=False)
    is_spf_v2_visible = models.BooleanField(_("SPFv2: Visible"), default=False)

    custom_service_for_request = models.ForeignKey("handling.HandlingRequest", null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True)
    availability = models.ManyToManyField("organisation.Organisation",
                                          verbose_name='Applicable Airport(s)',
                                          blank=True, through='HandlingServiceAvailability')
    always_included = models.BooleanField(_("Always Included?"), default=False,
                                          help_text='This service will be automatically applied to each S&F Request')
    organisations = models.ManyToManyField("organisation.Organisation",
                                           verbose_name='Applicable Unit(s)',
                                           help_text='Service usage will be locked only to selected organisations.',
                                           limit_choices_to={'operator_details__isnull': False,
                                                             'operator_details__type_id__in': [13, 14, 15, 16, 17]},
                                           blank=True,
                                           related_name='organisation_specific_handling_services',
                                           through='HandlingServiceOrganisationSpecific')
    tags = models.ManyToManyField("core.Tag", through='handling.HandlingServiceTag',
                                  blank=True, related_name='handling_services')
    represent_in_spf_as = models.ManyToManyField("handling.HandlingService",
                                                 verbose_name=_("Represent in SPF as"),
                                                 through='handling.HandlingServiceSpfRepresentation',
                                                 blank=True, related_name='spf_represented_by')
    dla_service = models.OneToOneField("organisation.DlaService", verbose_name=_("DLA Service"),
                                       related_name='handling_service',
                                       null=True, blank=True,
                                       on_delete=models.SET_NULL)

    objects = HandlingServiceManager()

    class Meta:
        ordering = ['name']
        db_table = 'handling_services'
        app_label = 'handling'

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        # Make cleanup on service type changing
        if self.pk and (self.is_dla or self.is_dla_v2):
            self.availability.clear()

        super().save(*args, **kwargs)

    @property
    def is_used(self):
        """Property that indicate does service used for any
        HandlingReqeust or no.

        Returns:
            bool: True if service used, otherwise False
        """
        return self.hr_services.exists()

    def get_availability(self, nocache=False):
        cache_result = cache.get(self.get_availability_cache_key, None)
        if not nocache and cache_result is not None:
            print('get_availability CACHE HIT')
            return cache_result
        else:
            print('get_availability CACHE MISS')
            availability_values = self.hs_availability.exclude(direction_id=None).values('airport', 'direction')
            availability_list = list(availability_values)
            cache.set(self.get_availability_cache_key, availability_list)
            cache.persist(self.get_availability_cache_key)
            return availability_list

    def get_availability_bool(self, nocache=False):
        cache_result = cache.get(self.get_availability_bool_cache_key, None)
        if not nocache and cache_result is not None:
            print('get_availability_bool CACHE HIT')
            return cache_result
        else:
            print('get_availability_bool CACHE MISS')
            availability_bool_values = self.availability.annotate(
                handling_service_id=F('handlingservice'),
                airport=F('pk'),
                arrival_count=Coalesce(Count(F('hs_availability'),
                                             filter=Q(hs_availability__direction='ARRIVAL'),
                                             output_field=IntegerField()), 0),
                arrival=Case(
                    When(arrival_count__gte=1, then=True),
                    default=False,
                    output_field=BooleanField()),
                departure_count=Coalesce(Count(F('hs_availability'),
                                               filter=Q(hs_availability__direction='DEPARTURE'),
                                               output_field=IntegerField()), 0),
                departure=Case(
                    When(departure_count__gte=1, then=True),
                    default=False,
                    output_field=BooleanField()),
            ).values('airport', 'arrival', 'departure')
            availability_bool_list = list(availability_bool_values)
            cache.set(self.get_availability_bool_cache_key, availability_bool_list)
            cache.persist(self.get_availability_bool_cache_key)
            return availability_bool_list

    @property
    def get_availability_cache_key(self):
        return f'handling_services_availability_{self.pk}'

    @property
    def get_availability_bool_cache_key(self):
        return f'handling_services_availability_bool_{self.pk}'

    def set_to_cache(self):
        self.get_availability(nocache=True)
        self.get_availability_bool(nocache=True)


@receiver(post_save, sender=HandlingService)
def handling_service_post_save_tasks(sender, instance, created, **kwargs): # noqa
    from ..utils.tags import update_handling_service_default_tags
    update_handling_service_default_tags(instance)


class HandlingServiceOrganisationSpecific(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Unit"),
                                     on_delete=models.CASCADE,
                                     related_name='handling_services')
    service = models.ForeignKey("handling.HandlingService",
                                verbose_name=_("Service"),
                                on_delete=models.CASCADE,
                                related_name='organisation_handling_services')

    class Meta:
        db_table = 'handling_services_organisations'
        app_label = 'handling'

    def __str__(self):
        return f'{self.organisation.details.registered_name}'


class HandlingServiceSpfRepresentation(models.Model):
    service = models.ForeignKey("handling.HandlingService",
                                verbose_name=_("Service"),
                                on_delete=models.CASCADE,
                                related_name='represented_by')
    represent_as = models.ForeignKey("handling.HandlingService",
                                     verbose_name=_("Represent As"),
                                     on_delete=models.CASCADE,
                                     related_name='represent')

    class Meta:
        db_table = 'handling_services_spf_representations'
        app_label = 'handling'


class HandlingServiceTag(models.Model):
    handling_service = models.ForeignKey("handling.HandlingService", on_delete=models.CASCADE)
    tag = models.ForeignKey("core.Tag", on_delete=models.CASCADE)

    class Meta:
        db_table = 'handling_services_tags'
        app_label = 'handling'

    def __str__(self):
        return f'{self.tag}'


class HandlingServiceAvailability(models.Model):
    airport = models.ForeignKey("organisation.Organisation", verbose_name=_("Airport"),
                                on_delete=models.CASCADE,
                                related_name='hs_availability')
    service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"),
                                on_delete=models.CASCADE,
                                related_name='hs_availability')
    direction = models.ForeignKey("handling.MovementDirection", verbose_name=_("Available On"),
                                  null=True,
                                  on_delete=models.CASCADE,
                                  db_column='direction_code')

    class Meta:
        db_table = 'handling_services_availability'
        app_label = 'handling'

    def __str__(self):
        if self.direction:
            return f'{self.service} available on {self.direction} in {self.airport}'
        return f'{self.service} attached to {self.airport}'


@receiver(post_save, sender=HandlingServiceAvailability)
def handling_service_availability_post_save_signal(sender, instance, created, **kwargs): # noqa
    instance.service.set_to_cache()


@receiver(post_delete, sender=HandlingServiceAvailability)
def handling_service_availability_post_delete_signal(sender, instance, **kwargs): # noqa
    instance.service.set_to_cache()
