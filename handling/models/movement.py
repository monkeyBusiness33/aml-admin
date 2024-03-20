import pytz
from django.db import models
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from timezonefinder import TimezoneFinder

from core.utils.model_diff import ModelDiffMixin
from handling.utils.activity_logging import movement_activity_logging
from handling.utils.amendment_session_helpers import update_amendment_session_services, create_amendment_session_record
from handling.utils.email_diff_generator import generate_diff_dict
from handling.utils.localtime import get_utc_from_airport_local_time
from handling.utils.movement_utils import movement_add_mandatory_services, movement_amendment


tf = TimezoneFinder()


class MovementDirection(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(_("Name"), max_length=50, null=True)

    class Meta:
        db_table = 'handling_movement_direction'
        app_label = 'handling'

    def __str__(self):
        return self.code


class HandlingRequestMovement(models.Model, ModelDiffMixin):
    IS_LOCAL_TIME_CHOICES = (
        (False, _("UTC")),
        (True, _("Local"))
    )

    request = models.ForeignKey("handling.HandlingRequest", on_delete=models.CASCADE, related_name='movement')
    direction = models.ForeignKey(MovementDirection, on_delete=models.RESTRICT, db_column='direction_code')
    date = models.DateTimeField(_("Date"), auto_now=False, auto_now_add=False)
    airport = models.ForeignKey("organisation.Organisation",
                                verbose_name=_("Airport"),
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    crew = models.PositiveIntegerField(_("Crew"))
    is_passengers_onboard = models.BooleanField(_("Pax Onboard?"), default=False)
    is_passengers_tbc = models.BooleanField(_("Is Passengers TBC?"), default=False)
    passengers = models.PositiveIntegerField(_("Passengers"), null=True, blank=True)
    comment = models.CharField(_("Comments"), max_length=1000, null=True, blank=True)
    special_requests = models.CharField(_("Special Requests"), max_length=1000, null=True, blank=True)
    ppr_number = models.CharField(_("PPR Number"), max_length=100, null=True, blank=True)

    # Meta tags
    amendment_fields = {'date', 'airport_id', 'crew', 'is_passengers_onboard', 'passengers'}
    is_amended = False
    movement_meta_prevent_sfr_save = False
    movement_meta_retain_fuel_order = False  # Do not reset Fuel confirmation on amendment
    movement_meta_retain_gh_confirmation = False  # Do not reset GH confirmation on amendment

    class Meta:
        db_table = 'handling_requests_movement'
        ordering = ['id']
        app_label = 'handling'

    def __str__(self):
        return f'{self.direction}'

    @property
    def direction_name(self):
        return self.direction.code.title()

    @property
    def direction_code(self):
        return str(self.direction_id).lower()

    @property
    def booking_completed(self):
        """
        Returns boolean value is all services has been reviewed for booking
        """
        return not self.hr_services.filter(booking_confirmed__isnull=True).exists()

    @property
    def date_capitalized(self):
        return self.date.strftime("%b-%d-%Y").upper()

    @property
    def time(self):
        return self.date.strftime("%H:%M")

    @property
    def datetime_capitalized(self):
        return self.date.strftime("%b-%d-%Y %H:%M").upper()

    @property
    def date_local(self):
        tz = tf.timezone_at(lng=float(self.request.airport.airport_details.longitude),
                            lat=float(self.request.airport.airport_details.latitude))
        timezone = pytz.timezone(tz)
        with_timezone = self.date.astimezone(timezone)
        return with_timezone

    @property
    def passengers_tiny_repr(self):
        if not self.is_passengers_onboard:
            return 'None'
        else:
            if self.is_passengers_tbc:
                return 'TBC'
            else:
                return str(self.passengers)

    @property
    def passengers_full_repr(self):
        if not self.is_passengers_onboard:
            return 'No Passengers'
        else:
            if self.is_passengers_tbc:
                return 'Passenger Number TBC'
            else:
                if self.passengers == 1:
                    return f'{self.passengers} Passenger onboard'
                else:
                    return f'{self.passengers} Passengers onboard'

    @property
    def crew_full_repr(self):
        return f'{self.crew} Crew onboard'

    def save(self, *args, **kwargs):
        updated_by = getattr(self, 'updated_by', None)
        handling_request_diff = None

        if hasattr(self, 'is_datetime_local'):
            if self.is_datetime_local:
                self.date = get_utc_from_airport_local_time(self.date, self.request.airport)

        # Finally localize date in cases when it still has no tz
        if self.date.tzinfo is None:
            self.date = pytz.utc.localize(self.date)

        if not self.pk:
            setattr(self, 'is_created', True)

        if self.pk:
            # Amendment Session for the GH Amendment Email
            fields_to_save_in_amendment_session = ['date', 'airport_id', 'is_passengers_onboard',
                                                   'is_passengers_tbc', 'passengers', ]

            if set(fields_to_save_in_amendment_session).intersection(self.changed_fields) and \
                not self.movement_meta_retain_gh_confirmation:
                # Set a flag for departure movement modification after arrival (as this now needs modified action btns)
                # Only do this if handling is otherwise already confirmed and there's no other amendment session open.
                # Pass it as a property of the HandlingRequest object, so that it can be set for newly created sessions
                is_departure_editing_grace_period = getattr(self.request, 'is_departure_editing_grace_period', None)
                self.request.set_is_departure_update_after_arrival = self.direction_id == 'DEPARTURE' \
                                                                     and is_departure_editing_grace_period \
                                                                     and self.request.is_handling_confirmed

                create_amendment_session_record(self.request)

            # Create amendment dict on movement update
            if not hasattr(self, 'is_created'):
                handling_request_diff = generate_diff_dict(self.request)

        super().save(*args, **kwargs)
        movement_add_mandatory_services(self)

        if not hasattr(self, 'is_created') and updated_by:
            movement_amendment(self, handling_request_diff)

            # Create Activity Log record for specified fields
            if not hasattr(self, 'activity_log_supress'):
                movement_activity_logging(movement=self, author=updated_by)


class HandlingRequestServices(models.Model, ModelDiffMixin):
    service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"),
                                on_delete=models.RESTRICT, related_name='hr_services')
    movement = models.ForeignKey("handling.HandlingRequestMovement", verbose_name=_("Movement"),
                                 on_delete=models.CASCADE, related_name='hr_services')
    booking_confirmed = models.BooleanField(_("Booking Confirmed"), null=True)
    note = models.CharField(_("Note"), null=True, blank=True, max_length=500)
    note_internal = models.CharField(_("Internal Note"), null=True, blank=True, max_length=500)
    booking_text = models.CharField(_("Details"), max_length=255, null=True, blank=True)
    booking_quantity = models.DecimalField(_("Quantity Required"),
                                           max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    booking_quantity_uom = models.ForeignKey("core.UnitOfMeasurement",
                                             verbose_name=_("Quantity Required UOM"),
                                             limit_choices_to={'is_fluid_uom': True},
                                             null=True, blank=True,
                                             on_delete=models.RESTRICT)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated At"), null=True, on_delete=models.SET_NULL)

    amendment_fields = {'note', 'booking_text', 'booking_quantity'}
    is_amended = False
    sfr_service_meta_prevent_sfr_save = False

    class Meta:
        db_table = 'handling_requests_services'
        app_label = 'handling'

    def __str__(self):
        return f'{self.service.name}'

    @property
    def service_repr(self):
        service_details = ''
        if self.booking_text:
            service_details = f' ({self.booking_text})'
        elif self.booking_quantity:
            service_details = f' ({self.booking_quantity} {self.booking_quantity_uom.code})'

        return f'{self.service.name}{service_details}'

    def save(self, *args, **kwargs):
        is_created = not bool(self.pk)
        old_sfr_instance_diff = None

        if not self.pk:
            setattr(self, 'is_created', True)
            if self.booking_quantity:
                self.booking_quantity_uom = self.service.quantity_selection_uom

        if not hasattr(self, 'supress_amendment'):
            from handling.models import HandlingRequest
            old_sfr_instance = HandlingRequest.objects.filter(pk=self.movement.request.pk).first()
            if old_sfr_instance:
                old_sfr_instance_diff = generate_diff_dict(handling_request=old_sfr_instance)

        amendment_fields = ['booking_text', 'booking_quantity']
        if is_created or set(amendment_fields).intersection(self.changed_fields):
            update_amendment_session_services(handling_request=self.movement.request,
                                              direction_code=self.movement.direction_id,
                                              hr_service=self,
                                              is_added=is_created,
                                              )

        super().save(*args, **kwargs)

        # Process amendment
        if old_sfr_instance_diff and not hasattr(self, 'supress_amendment'):
            if hasattr(self, 'is_created'):
                self.movement.activity_log.create(
                    author=self.updated_by,
                    record_slug='sfr_movement_service_added',
                    details=f'{self.service.name}'
                )
            if hasattr(self, 'is_created') or self.amendment_fields.intersection(self.changed_fields):
                self.is_amended = True
                from handling.utils.client_notifications import handling_request_updated_services_push_notification
                handling_request_updated_services_push_notification(self.movement.request)
                self.movement.request.old_instance_diff = old_sfr_instance_diff
                self.movement.request.is_services_amended = True
                self.movement.request.updated_by = self.updated_by
                if not self.sfr_service_meta_prevent_sfr_save:
                    self.movement.request.save()

    @property
    def is_service_deletable(self):
        handling_request = self.movement.request
        if self.movement.is_passengers_onboard and self.service.codename == 'passengers_handling':
            return False
        return all(
            (
                not self.movement.request.is_expired,
                handling_request.status not in (4, 5, 7),
                not self.booking_confirmed,
            )
        )


@receiver(pre_delete, sender=HandlingRequestServices)
def process_handling_service_gh_amendment(sender, instance, **kwargs): # noqa
    update_amendment_session_services(handling_request=instance.movement.request,
                                      direction_code=instance.movement.direction_id,
                                      hr_service=instance,
                                      is_removed=True)
    from handling.utils.client_notifications import handling_request_updated_services_push_notification
    handling_request_updated_services_push_notification(instance.movement.request)


@receiver(post_delete, sender=HandlingRequestServices)
def process_handling_service_gh_amendment(sender, instance, **kwargs): # noqa

    instance.movement.activity_log.create(
        author=getattr(instance, 'updated_by', None),
        record_slug='sfr_movement_service_removed',
        details=f'{instance.service.name}'
    )

    old_sfr_instance_diff = generate_diff_dict(handling_request=instance.movement.request)
    instance.movement.request.old_instance_diff = old_sfr_instance_diff
    instance.movement.request.is_services_amended = True
    instance.movement.request.updated_by = instance.updated_by
    instance.movement.request.save()
