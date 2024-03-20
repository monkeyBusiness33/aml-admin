from django.core.validators import MaxLengthValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.forms import phone_regex_validator


class HandlerType(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    is_fbo = models.BooleanField(_("Is FBO?"), default=False)

    class Meta:
        ordering = ['name']
        db_table = 'organisations_handler_types'

    def __str__(self):
        return f'{self.name}'


class HandlerDetails(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        on_delete=models.CASCADE,
                                        related_name='handler_details')
    airport = models.ForeignKey("organisation.Organisation", verbose_name=_("Airport"),
                                limit_choices_to={'details__type_id': 8,
                                                  'airport_details__isnull': False},
                                related_name='airport_handlers',
                                on_delete=models.RESTRICT)
    handler_type = models.ForeignKey("organisation.HandlerType",
                                     verbose_name=_("Handler Type"),
                                     on_delete=models.RESTRICT)
    handles_ba_ga = models.BooleanField(_("Handles BA/GA?"), default=False)
    handles_airlines = models.BooleanField(_("Handles Airlines?"), default=False)
    handles_cargo = models.BooleanField(_("Handles Cargo?"), null=True)
    handles_military = models.BooleanField(_("Handles Military?"), default=False)
    contact_phone = models.CharField(_("Contact Phone"), max_length=128,
                                     null=True, blank=True,
                                     validators=[phone_regex_validator],
                                     )
    contact_email = models.EmailField(_("Contact Email"), max_length=254,
                                      null=True, blank=True)
    ops_phone = models.CharField(_("Ops Phone"), max_length=128,
                                 null=True, blank=True,
                                 validators=[phone_regex_validator],
                                 )
    ops_email = models.EmailField(_("Ops Email"), max_length=254,
                                  null=True, blank=True)
    ops_frequency = models.DecimalField(_("Ops Frequency"), max_digits=6, decimal_places=3,
                                        null=True, blank=True)
    is_in_gat = models.BooleanField(_("In GAT?"), null=True, blank=True)
    is_in_airport_terminal = models.BooleanField(_("In Airport Terminal?"), null=True, blank=True)
    is_in_cargo_centre = models.BooleanField(_("In Cargo Centre?"), default=False)
    has_pax_lounge = models.BooleanField(_("Has Pax Lounge?"), null=True, blank=True)
    has_crew_room = models.BooleanField(_("Has Crew Room?"), null=True, blank=True)
    has_vip_lounge = models.BooleanField(_("Has VIP lounge?"), null=True, blank=True)

    class Meta:
        db_table = 'organisations_handler_details'

    def __str__(self):
        return f'{self.organisation}'

    @property
    def is_ipa(self):
        return hasattr(self, 'ipa_details')


class HandlerCancellationBand(models.Model):
    handler = models.ForeignKey("organisation.Organisation", verbose_name=_("Handler"),
                                related_name='handler_cancellation_bands',
                                on_delete=models.CASCADE)
    notification_band_start_hours = models.PositiveSmallIntegerField(_("Notice Period Start (Hours)"),
                                                                     validators=[MaxValueValidator(99)],
                                                                     )
    notification_band_end_hours = models.PositiveSmallIntegerField(_("Notice Period End (Hours)"),
                                                                   null=True, blank=True)

    class Meta:
        db_table = 'organisations_handler_cancellation_bands'

    def __str__(self):
        return f'{self.pk}'


class HandlerCancellationBandTerm(models.Model):
    cancellation_band = models.ForeignKey("organisation.HandlerCancellationBand", verbose_name=_("Cancellation Band"),
                                          related_name='cancellation_terms',
                                          on_delete=models.CASCADE)
    penalty_specific_service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"),
                                                 related_name='handler_cancellation_bands_terms',
                                                 null=True, blank=True,
                                                 on_delete=models.CASCADE)
    penalty_percentage = models.DecimalField(_("Penalty Percentage"), max_digits=5, decimal_places=2,
                                             null=True, blank=True)
    penalty_amount = models.DecimalField(_("Penalty Amount"), max_digits=10, decimal_places=2,
                                         null=True, blank=True)
    penalty_amount_currency = models.ForeignKey("core.Currency", verbose_name=_("Currency"),
                                                related_name='handler_cancellation_bands_terms',
                                                null=True, blank=True,
                                                on_delete=models.RESTRICT)

    class Meta:
        db_table = 'organisations_handler_cancellation_bands_terms'

    def __str__(self):
        return f'{self.pk}'

    def get_penalty_display(self):
        if self.penalty_percentage:
            return f'{self.penalty_percentage}%'
        if self.penalty_amount_currency:
            return f'{self.penalty_amount_currency.symbol}{self.penalty_amount} {self.penalty_amount_currency.code}'
