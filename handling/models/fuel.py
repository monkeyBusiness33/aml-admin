from django.db import models
from django.utils.translation import gettext_lazy as _

from app.storage_backends import FuelReleaseStorage
from core.utils.model_diff import ModelDiffMixin


class HandlingRequestFuelBooking(models.Model, ModelDiffMixin):
    handling_request = models.OneToOneField("handling.HandlingRequest",
                                            verbose_name=_("Servicing & Fueling Request"),
                                            related_name='fuel_booking',
                                            on_delete=models.CASCADE)
    ipa = models.ForeignKey("organisation.Organisation", verbose_name=_("IPA"),
                            limit_choices_to={'ipa_locations__isnull': False},
                            on_delete=models.CASCADE,
                            related_name='handling_requests_fuel_bookings')
    dla_contracted_fuel = models.BooleanField(_("Coordination with DLA Contracted Supplier?"),
                                              default=False)
    fuel_order_number = models.CharField(_("Fuel Order Number"),
                                         max_length=50, null=True, blank=True)
    processed_by = models.CharField(_("Processed By"), max_length=50)
    fuel_release = models.FileField(verbose_name=_("Upload Fuel Release"),
                                    storage=FuelReleaseStorage(),
                                    null=True, blank=True)
    is_confirmed = models.BooleanField(_("Fuel Booking Confirmed"), default=True)

    class Meta:
        db_table = 'handling_requests_fuel_confirmations'
        app_label = 'handling'

    def save(self, *args, **kwargs):
        updated_by = getattr(self, 'updated_by', None)
        is_created = not self.pk
        super().save(*args, **kwargs)
        self.handling_request.updated_by = updated_by
        self.handling_request.is_new = False  # Mark S&F Request as not new for quest confirmation
        self.handling_request.save()
        if {'ipa', 'dla_contracted_fuel', 'fuel_order_number', 'processed_by', 'is_confirmed'}.intersection(
                self.changed_fields) or is_created:
            self.handling_request.activity_log.create(
                author=updated_by,
                author_text=self.processed_by if not updated_by else None,
                record_slug='sfr_fuel_booking_confirmation',
                details='Fuel Booking has been confirmed',
            )

        if 'fuel_release' in self.changed_fields and not \
                self.get_field_diff('fuel_release')[0] and self.get_field_diff('fuel_release')[1]:
            self.handling_request.activity_log.create(
                author=updated_by or None,
                author_text=self.processed_by if not updated_by else None,
                record_slug='sfr_fuel_release_uploaded',
                details='Fuel Release File Added',
            )

        if 'fuel_release' in self.changed_fields and not self.get_field_diff('fuel_release')[1]:
            self.handling_request.activity_log.create(
                author=updated_by,
                record_slug='sfr_fuel_release_removed',
                details='Fuel Release File Removed',
            )
