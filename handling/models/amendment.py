from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class HandlingRequestAmendment(models.Model):
    request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                related_name='amendments',
                                on_delete=models.CASCADE)
    details = models.CharField(_("Amendment"), max_length=1000)
    tail_number_changed = models.BooleanField(default=False, null=True)
    created_at = models.DateTimeField(_("Date"), auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("User"),
                                   null=True,
                                   on_delete=models.CASCADE)
    created_by_text = models.CharField(_("Person (guest)"), max_length=50, null=True)

    class Meta:
        db_table = 'handling_requests_amendments'
        ordering = ['-created_at']
        app_label = 'handling'


class HandlingRequestAmendmentSession(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         related_name='amendment_sessions',
                                         on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    is_gh_opened = models.BooleanField(_("Is GH Amendment Opened"), default=True)
    is_gh_sent = models.BooleanField(_("Is sent to GH"), default=False)
    # S&F Request Fields (stores original values, that ones are before amendment)
    callsign = models.CharField(_("Callsign"), max_length=50, null=True, blank=True)
    tail_number = models.ForeignKey("aircraft.AircraftHistory",
                                    verbose_name=_("Tail Number"),
                                    limit_choices_to={'details_rev__isnull': False},
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    aircraft_type = models.ForeignKey("aircraft.AircraftType",
                                      verbose_name=_("Aircraft Type"),
                                      null=True, blank=True,
                                      on_delete=models.CASCADE)

    arrival_date = models.DateTimeField(_("Arrival Date"), auto_now=False, auto_now_add=False, null=True)
    arrival_airport = models.ForeignKey("organisation.Organisation",
                                        verbose_name=_("Arrival From"),
                                        related_name='amendment_sessions_arrival_from',
                                        null=True, on_delete=models.SET_NULL)
    arrival_is_passengers_onboard = models.BooleanField(_("Pax Onboard?"), null=True)
    arrival_is_passengers_tbc = models.BooleanField(_("Is Passengers TBC?"), null=True)
    arrival_passengers = models.PositiveIntegerField(_("Arrival Passengers"), null=True, blank=True)

    departure_date = models.DateTimeField(_("Departure Date"), auto_now=False, auto_now_add=False, null=True)
    departure_airport = models.ForeignKey("organisation.Organisation",
                                          verbose_name=_("Departure To"),
                                          related_name='amendment_sessions_departure_to',
                                          null=True, on_delete=models.SET_NULL)
    departure_is_passengers_onboard = models.BooleanField(_("Pax Onboard?"), null=True)
    departure_is_passengers_tbc = models.BooleanField(_("Is Passengers TBC?"), null=True)
    departure_passengers = models.PositiveIntegerField(_("Departure Passengers"), null=True, blank=True)

    services = models.ManyToManyField("handling.HandlingService",
                                      verbose_name='Services',
                                      blank=True, through='HandlingRequestAmendmentSessionService')

    is_departure_update_after_arrival = models.BooleanField(_("Is Departure Change After Arrival?"), default=False)

    class Meta:
        db_table = 'handling_requests_amendment_sessions'
        app_label = 'handling'

    @property
    def get_arrival_date(self):
        return self.arrival_date if self.arrival_date else self.handling_request.arrival_movement.date

    @property
    def get_departure_date(self):
        return self.departure_date if self.departure_date else self.handling_request.departure_movement.date

    @property
    def get_callsign(self):
        return self.callsign if self.callsign else self.handling_request.callsign

    @property
    def is_arrival_passengers_amended(self):
        if self.arrival_is_passengers_onboard != self.handling_request.arrival_movement.is_passengers_onboard or \
                self.arrival_is_passengers_tbc != self.handling_request.arrival_movement.is_passengers_tbc or \
                self.arrival_passengers != self.handling_request.arrival_movement.passengers:
            return True

    @property
    def arrival_passengers_full_repr(self):
        if not self.arrival_is_passengers_onboard:
            return 'No Passengers'
        else:
            if self.arrival_is_passengers_tbc:
                return 'Passenger Number TBC'
            else:
                if self.arrival_passengers == 1:
                    return f'{self.arrival_passengers} Passenger onboard'
                else:
                    return f'{self.arrival_passengers} Passengers onboard'

    @property
    def is_departure_passengers_amended(self):
        if self.departure_is_passengers_onboard != self.handling_request.departure_movement.is_passengers_onboard or \
                self.departure_is_passengers_tbc != self.handling_request.departure_movement.is_passengers_tbc or \
                self.departure_passengers != self.handling_request.departure_movement.passengers:
            return True

    @property
    def departure_passengers_full_repr(self):
        if not self.departure_is_passengers_onboard:
            return 'No Passengers'
        else:
            if self.departure_is_passengers_tbc:
                return 'Passenger Number TBC'
            else:
                if self.departure_passengers == 1:
                    return f'{self.departure_passengers} Passenger onboard'
                else:
                    return f'{self.departure_passengers} Passengers onboard'

    def is_services_amended(self, direction_code):
        for session_service in self.session_services.filter(direction_id=direction_code):
            if session_service.is_added or session_service.is_removed:
                return True

            from handling.models import HandlingRequestServices
            handling_service = HandlingRequestServices.objects.filter(
                (~Q(booking_quantity=session_service.booking_quantity) | ~Q(booking_text=session_service.booking_text)),
                service=session_service.service,
                movement__direction=session_service.direction,
                movement__request=self.handling_request,
            ).exists()
            if handling_service:
                return True

        return False

    @property
    def is_arrival_services_amended(self):
        return self.is_services_amended('ARRIVAL')

    @property
    def is_departure_services_amended(self):
        return self.is_services_amended('DEPARTURE')

    @property
    def get_arrival_services(self):
        return self.session_services.filter(direction_id='ARRIVAL').all()

    @property
    def get_departure_services(self):
        return self.session_services.filter(direction_id='DEPARTURE').all()


class HandlingRequestAmendmentSessionService(models.Model):
    amendment_session = models.ForeignKey("handling.HandlingRequestAmendmentSession",
                                          verbose_name=_("Amendment Session"),
                                          related_name='session_services',
                                          on_delete=models.CASCADE)
    service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"),
                                related_name='amendment_session_services',
                                on_delete=models.RESTRICT)
    direction = models.ForeignKey("handling.MovementDirection", verbose_name=_("Movement"),
                                  related_name='amendment_session_services',
                                  db_column='direction_code',
                                  on_delete=models.CASCADE)
    is_added = models.BooleanField(_("Is Added?"), default=False)
    is_removed = models.BooleanField(_("Is Removed"), default=False)
    booking_quantity = models.DecimalField(_("Quantity Required"),
                                           max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    booking_quantity_uom = models.ForeignKey("core.UnitOfMeasurement",
                                             verbose_name=_("Quantity Required UOM"),
                                             limit_choices_to={'is_fluid_uom': True},
                                             null=True, blank=True,
                                             on_delete=models.RESTRICT)
    booking_text = models.CharField(_("Details"), max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'handling_requests_amendment_sessions_services'
        app_label = 'handling'

    @property
    def amendment_repr(self):
        from handling.models import HandlingRequestServices
        handling_service = HandlingRequestServices.objects.filter(
            service=self.service,
            movement__direction=self.direction,
            movement__request=self.amendment_session.handling_request,
        ).first()
        if handling_service:
            value_prev = None
            value_new = None
            if handling_service.booking_quantity != self.booking_quantity:
                value_prev = f'{self.booking_quantity} {self.booking_quantity_uom.description_plural}'
                value_new = f'{handling_service.booking_quantity} ' \
                            f'{handling_service.booking_quantity_uom.description_plural}'
            elif handling_service.booking_text != self.booking_text:
                value_prev = self.booking_text
                value_new = handling_service.booking_text

            if value_prev and value_new:
                text = ' (<span class="old-detail">{value_prev}</span> >>> ' \
                       '<span class="new-detail">{value_new}</span>)'.format(
                            value_prev=value_prev,
                            value_new=value_new,
                        )
                return text
        if self.booking_quantity:
            return f' ({self.booking_quantity} {self.booking_quantity_uom.description_plural})'
        if self.booking_text:
            return f' ({self.booking_text})'
        return ''
