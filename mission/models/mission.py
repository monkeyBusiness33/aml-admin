import logging
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import OuterRef, Subquery, Case, When, Value, IntegerField, Q, Sum, F, DateTimeField, Max, \
    CharField
from django.db.models.functions import Coalesce, Concat
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from sql_util.aggregates import SubquerySum

from app.storage_backends import AirCardPhotoStorage
from core.utils.datatables_functions import get_datatable_badge
from core.utils.model_diff import ModelDiffMixin
from handling.models import HandlingRequest
from handling.utils.statuses_generators import get_fuel_booking_status_circle, get_ground_handling_status_circle
from mission.utils.activity_logging import mission_activity_logging, mission_leg_activity_logging
from mission.utils.legs_utils import mission_leg_after_save, mission_leg_pre_save
from mission.utils.mission_utils import mission_on_update_actions, mission_after_save, calculate_mission_status_flags

logger = logging.getLogger(__name__)


class MissionStatusFlags(models.Model):
    mission = models.OneToOneField("mission.Mission", verbose_name=_("Mission"),
                                   related_name='status_flags',
                                   on_delete=models.CASCADE)
    has_sfr = models.BooleanField(_("Has Any S&F Request"), default=False)
    has_sfr_new = models.BooleanField(_("Has New S&F Request"), default=False)
    has_sfr_amended = models.BooleanField(_("Has Amended S&F Request"), default=False)
    has_sfr_in_progress = models.BooleanField(_("Has In Progress S&F Request"), default=False)
    has_sfr_confirmed = models.BooleanField(_("Has Confirmed S&F Request"), default=False)

    class Meta:
        db_table = 'missions_status_details'


class MissionManager(models.QuerySet):
    def include_details(self):
        from chat.models import Conversation
        mission_leg_sq = MissionLeg.objects.filter(mission_id=OuterRef('pk'), is_cancelled=False)
        chat_conversation_sq = Conversation.objects.filter(mission_id=OuterRef('pk'))

        qs = self.annotate(
            mission_number_concat=Concat('mission_number_prefix', 'mission_number',
                                         output_field=CharField()),
            chat_conversation_id=Subquery(chat_conversation_sq.values('pk')[:1]),
            start_date_val=Subquery(mission_leg_sq.filter(previous_leg__isnull=True).values('departure_datetime')[:1]),
            end_date_val=Subquery(mission_leg_sq.filter(next_leg__isnull=True).values('arrival_datetime')[:1]),

            status_code=Case(
                # Legend:
                # 0 - Error
                # 1 - Cancelled
                # 2 - Draft
                # 3 - Confirmed
                # 4 - In Progress
                # 5 - Completed
                # 6 - Amended
                # 10 - New
                When(is_cancelled=True, then=Value(1)),

                # 2 - Confirmed
                When(is_confirmed=False, then=Value(2)),

                # 5 - Completed
                When(end_date_val__lt=timezone.now(), then=Value(5)),

                # 7 - New
                When(status_flags__has_sfr_new=True, then=Value(10)),

                # 6 - Amended
                When(status_flags__has_sfr_amended=True, then=Value(6)),

                # 4 - In Progress
                When(status_flags__has_sfr_in_progress=True, then=Value(4)),

                # 3 - Confirmed
                When((Q(status_flags__has_sfr=False) | Q(status_flags__has_sfr_confirmed=True)), then=Value(3)),

                default=Value(0),
                output_field=IntegerField(),
            ),
            status_index=Case(
                When(status_code=1, then=Value(50)),
                When(status_code=2, then=Value(30)),
                When(status_code=3, then=Value(20)),
                When(status_code=4, then=Value(10)),
                When(status_code=5, then=Value(40)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            date_index=Case(
                When(status_code=5, then=F('end_date_val')),
                default=timezone.now(),
                output_field=DateTimeField()
            )
        )
        return qs


class Mission(models.Model, ModelDiffMixin):
    STATUS_DETAILS = {
        0: {'code': 0, 'detail': 'Error', 'background_color': '#fff', 'text_color': '#e11d48'},
        1: {'code': 1, 'detail': 'Cancelled', 'background_color': '#111827', 'text_color': '#fff'},
        2: {'code': 2, 'detail': 'Draft', 'background_color': '#CAF0FE', 'text_color': '#1F2937'},
        3: {'code': 3, 'detail': 'Confirmed', 'background_color': '#10b981', 'text_color': '#fff'},
        4: {'code': 4, 'detail': 'In Progress', 'background_color': '#e5e56b', 'text_color': '#1F2937'},
        5: {'code': 5, 'detail': 'Completed', 'background_color': '#D2FFE3', 'text_color': '#374151'},
        6: {'code': 6, 'detail': 'Amended', 'background_color': '#fba918', 'text_color': '#1F2937'},
        10: {'code': 10, 'detail': 'New', 'background_color': '#1E90FF', 'text_color': '#fff'},
    }

    PACKET_PDF_AVAILABLE_STATUSES = [3, 5, 6]

    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Unit"),
                                     related_name='missions',
                                     on_delete=models.CASCADE)
    mission_number_prefix = models.CharField(_("Mission Number Prefix"), max_length=20, null=True, blank=True)
    mission_number = models.CharField(_("Mission Number"), max_length=50, null=True, blank=True)
    apacs_number = models.CharField(_("APACS Number"), max_length=50, null=True, blank=True)
    apacs_url = models.URLField(_("APACS Number"), null=True, blank=True)
    callsign = models.CharField(_("Callsign"), max_length=50, null=True, blank=True)
    is_amended_callsign = models.BooleanField(_("Is Callsign Amended?"), default=False)
    type = models.ForeignKey("handling.HandlingRequestType", verbose_name=_("Mission Type"),
                             related_name='missions',
                             on_delete=models.CASCADE)
    aircraft_type = models.ForeignKey("aircraft.AircraftType", verbose_name=_("Aircraft Type"),
                                      related_name='missions',
                                      on_delete=models.CASCADE)
    aircraft = models.ForeignKey("aircraft.AircraftHistory", verbose_name=_("Tail Number"),
                                 null=True, blank=True,
                                 related_name='missions',
                                 on_delete=models.CASCADE)
    air_card_prefix = models.ForeignKey("core.AirCardPrefix",
                                        verbose_name=_("AIR Card Prefix"),
                                        null=True, blank=True,
                                        on_delete=models.CASCADE)
    air_card_number = models.IntegerField(_("AIR Card Number"), null=True, blank=True)
    air_card_expiration = models.CharField(_("AIR Card Expiration"), max_length=5, null=True, blank=True)
    air_card_photo = models.FileField(storage=AirCardPhotoStorage(), null=True, blank=True)
    is_confirmed = models.BooleanField(_("Is Confirmed?"), default=False)
    is_cancelled = models.BooleanField(_("Is Cancelled?"), default=False)
    assigned_mil_team_member = models.ForeignKey("user.Person", verbose_name=_("Assigned Mil Team Member"),
                                                 related_name='assigned_missions',
                                                 null=True, blank=True,
                                                 on_delete=models.SET_NULL)
    requesting_person = models.ForeignKey("user.Person", verbose_name=_("Requesting Person"),
                                          related_name='requested_missions',
                                          on_delete=models.CASCADE)
    mission_planner = models.ForeignKey("user.Person", verbose_name=_("Requesting Person"),
                                        null=True, blank=True,
                                        related_name='planner_missions',
                                        on_delete=models.SET_NULL)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"),
                                   related_name='created_missions',
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    crew = models.ManyToManyField("user.Person", verbose_name='Mission Crew', blank=False, related_name='crew_missions',
                                  through='MissionCrewPosition')

    objects = MissionManager().as_manager()

    # Meta
    meta_is_first_save = None
    meta_is_partial_save = None

    class Meta:
        db_table = 'missions'
        ordering = ['-created_at']
        app_label = 'mission'

    def save(self, *args, **kwargs):
        if settings.DEBUG:
            logger.info('Mission: Saving...')
        updated_by = getattr(self, 'updated_by', None)
        self.meta_is_first_save = not self.pk  # Will be True only on first save

        if not self.pk:
            setattr(self, 'is_created', True)

        if self.pk:
            if not hasattr(self, 'is_created'):
                mission_on_update_actions(self)

        super().save(*args, **kwargs)
        # Create Activity Log record for specified fields
        if not hasattr(self, 'activity_log_supress'):
            mission_activity_logging(mission=self, author=updated_by)

        # Create or Update S&F Requests
        if not self.meta_is_partial_save:
            mission_after_save(self)

        calculate_mission_status_flags(self)

    def get_absolute_url(self, app_mode='ops_portal'):
        if app_mode == 'ops_portal':
            return reverse('admin:missions_details', args=[str(self.id)])
        if app_mode == 'dod_portal':
            return reverse('dod:missions_details', args=[str(self.id)])

    @property
    def mission_number_repr(self):
        return f'{self.mission_number_prefix or ""}{self.mission_number or ""}'

    @property
    def status(self):
        if not hasattr(self, 'status_code'):
            instance = Mission.objects.include_details().filter(pk=self.pk).first()
        else:
            instance = self
        status_code = getattr(instance, 'status_code', 0)
        return self.STATUS_DETAILS[status_code]

    def get_status_badge(self):
        status_code = getattr(self, 'status_code', 0)
        status_html = get_datatable_badge(
            badge_text=self.STATUS_DETAILS[status_code]['detail'],
            badge_class='datatable-badge-normal',
            background_color=self.STATUS_DETAILS[status_code]['background_color'],
            text_color=self.STATUS_DETAILS[status_code]['text_color'],
        )
        return status_html

    @cached_property
    def active_legs(self):
        from mission.models import MissionLegCargoPayload
        cargo_payload_sq = MissionLegCargoPayload.objects.filter(
            mission_legs_intermediate__mission_leg=OuterRef('pk'),
        ).order_by().values('mission_legs_intermediate__mission_leg').annotate(
            total_weight=Sum(F('weight') * F('quantity'))
        ).values('total_weight')

        return self.legs.filter(is_cancelled=False).prefetch_related(
            'departure_location__details',
            'departure_location__airport_details',
            'arrival_location__details',
            'arrival_location__airport_details',
            'next_leg',
            'turnaround__handling_request',
        ).annotate(
            payload_passengers_lbs=Coalesce(SubquerySum('passengers__weight'), 0),
            payload_cargo_lbs=Coalesce(Subquery(cargo_payload_sq), 0),
            payload_total_lbs=F('payload_passengers_lbs') + F('payload_cargo_lbs'),
        ).order_by('sequence_id')

    @property
    def active_legs_sequences_for_table(self):
        a = list(self.active_legs.values_list('sequence_id', flat=True))[:-1]
        b = list(self.active_legs.values_list('sequence_id', flat=True))[-1:]
        return a, b

    @property
    def active_legs_pairs(self):
        return zip(self.active_legs[::2], self.active_legs[1::2])

    @property
    def active_legs_adjacent_pairs(self):
        return zip(self.active_legs, self.active_legs[1:])

    @cached_property
    def passengers_max(self):
        return self.active_legs.aggregate(Max('pob_pax'))['pob_pax__max'] or 0

    @property
    def active_turnarounds(self):
        return MissionTurnaround.objects.filter(mission_leg__in=self.active_legs)

    @property
    def conversation_id(self):
        if hasattr(self, 'chat_conversation_id'):
            return self.chat_conversation_id
        chat_conversation = self.chat_conversations.first()
        return chat_conversation.pk if chat_conversation else None

    @property
    def start_date(self):
        if hasattr(self, 'start_date_val'):
            return self.start_date_val
        start_leg = self.legs.filter(previous_leg__isnull=True).first()
        return start_leg.departure_datetime if start_leg else None

    @property
    def end_date(self):
        if hasattr(self, 'end_date_val'):
            return self.end_date_val
        final_leg = self.legs.filter(next_leg__isnull=True).first()
        return final_leg.arrival_datetime if final_leg else None

    @cached_property
    def is_urgent(self):
        date_48h_before = self.start_date - timedelta(hours=48)
        return date_48h_before <= timezone.now() <= self.start_date

    @cached_property
    def requesting_person_position(self):
        position = self.organisation.organisation_people.filter(person=self.requesting_person).first()
        return position

    @property
    def is_editable(self):
        return all([
            not self.is_cancelled,
            self.end_date > timezone.now(),
        ])

    @property
    def handling_requests(self):
        from handling.models import HandlingRequest
        return HandlingRequest.objects.detailed_list().filter(mission_turnaround__mission_leg__mission=self)

    @property
    def turnarounds(self):
        return MissionTurnaround.objects.filter(mission_leg__mission=self, mission_leg__is_cancelled=False)

    @property
    def attached_documents(self):
        from handling.models import HandlingRequestDocument
        qs = HandlingRequestDocument.objects.filter(
            Q(mission=self) |
            Q(mission_leg__mission=self) |
            Q(handling_request__mission_turnaround__mission_leg__mission=self)
        )
        return qs

    @cached_property
    def packet_pdf_details(self):
        docs_total_qs = self.active_legs.filter(arrival_aml_service=True, turnaround__handling_request__isnull=False)
        docs_available_qs = HandlingRequest.objects.with_status().filter(
            mission_turnaround__mission_leg__mission=self,
            status__in=HandlingRequest.IS_PDF_AVAILABLE_STATUS_CODES
        )

        docs_total = docs_total_qs.count()
        docs_available = docs_available_qs.count()
        is_available = self.status['code'] in self.PACKET_PDF_AVAILABLE_STATUSES
        data = {
            'is_available': is_available,
            'docs_total': docs_total,
            'docs_available': docs_available,
            'is_full': docs_available == docs_total and is_available,
        }
        return data

    @property
    def payload_lbs(self):
        # Calculate Mission Payload LBS
        from mission.models import MissionLegPassengersPayload
        passengers_payload = MissionLegPassengersPayload.objects.filter(
            mission_leg__mission=self,
            mission_leg__is_cancelled=False,
        ).aggregate(total_weight=Sum(F('weight')))

        from mission.models import MissionLegCargoPayload
        cargo_payload = MissionLegCargoPayload.objects.filter(
            mission_leg__mission=self,
            mission_leg__is_cancelled=False,
        ).annotate(subtotal_weight=Sum('weight') * F('quantity')).aggregate(total_weight=Sum(F('subtotal_weight')))

        if not passengers_payload['total_weight'] and not cargo_payload['total_weight']:
            return None

        final_weight = 0
        final_weight += passengers_payload['total_weight'] or 0
        final_weight += cargo_payload['total_weight'] or 0
        return final_weight


@receiver(post_save, sender=Mission)
def mission_post_save_signal(sender, instance, created, **kwargs): # noqa
    if not instance.mission_number:
        instance.mission_number = instance.pk
        instance.meta_is_partial_save = True
        instance.save()


class MissionLegManager(models.QuerySet):
    def include_mission_and_sfr_status(self):
        mission_leg_sq = MissionLeg.objects.filter(mission_id=OuterRef('mission_id'), is_cancelled=False)

        qs = self.annotate(
            mission_start_date_val=Subquery(
                mission_leg_sq.filter(previous_leg__isnull=True).values('departure_datetime')[:1]),
            mission_end_date_val=Subquery(mission_leg_sq.filter(next_leg__isnull=True).values('arrival_datetime')[:1]),
            mission_status_code=Case(
                # Legend:
                # 0 - Error
                # 1 - Cancelled
                # 2 - Draft
                # 3 - Confirmed
                # 4 - In Progress
                # 5 - Completed
                When(mission__is_cancelled=True, then=Value(1)),
                When(mission__is_confirmed=False, then=Value(2)),

                # 7 - New
                When(mission__status_flags__has_sfr_new=True, then=Value(10)),

                # 6 - Amended
                When(mission__status_flags__has_sfr_amended=True, then=Value(6)),

                # 4 - In Progress
                When(mission__status_flags__has_sfr_in_progress=True, then=Value(4)),

                # 3 - Confirmed
                When(
                    (Q(mission__status_flags__has_sfr=False) | Q(mission__status_flags__has_sfr_confirmed=True)),
                    then=Value(3)
                ),

                # 5 - Completed
                When(mission_end_date_val__lt=timezone.now(), then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            sfr_fuel_status_code=Case(
                # Legend:
                # 0 - Error
                # 1 - No Fuel
                # 2 - No action started
                # 3 - Confirmed (No Fuel Release)
                # 4 - Confirmed (DLA Contracted Location)
                # 5 - Confirmed
                When(turnaround__handling_request__fuel_required__isnull=True, then=Value(1)),
                When(turnaround__handling_request__fuel_required__isnull=False,
                     turnaround__handling_request__fuel_booking__isnull=True, then=Value(2)),
                When(turnaround__handling_request__fuel_required__isnull=False,
                     turnaround__handling_request__fuel_booking__isnull=False,
                     turnaround__handling_request__fuel_booking__dla_contracted_fuel=False,
                     turnaround__handling_request__fuel_booking__fuel_release='', then=Value(3)),
                When(turnaround__handling_request__fuel_required__isnull=False,
                     turnaround__handling_request__fuel_booking__dla_contracted_fuel=True, then=Value(4)),
                When((Q(turnaround__handling_request__fuel_required__isnull=False) & Q(
                    turnaround__handling_request__fuel_booking__dla_contracted_fuel=False) & ~Q(
                    turnaround__handling_request__fuel_booking__fuel_release='')), then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            ground_handling_status_code=Case(
                # Legend:
                # 0 - Error
                # 1 - No action started
                # 2 - In Process
                # 3 - Confirmed
                When(turnaround__handling_request__handling_agent__isnull=True, then=Value(1)),
                When(turnaround__handling_request__handling_agent__isnull=False,
                     turnaround__handling_request__is_handling_confirmed=False, then=Value(2)),
                When(turnaround__handling_request__handling_agent__isnull=False,
                     turnaround__handling_request__is_handling_confirmed=True, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        return qs


class MissionLeg(models.Model, ModelDiffMixin):
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                related_name='legs',
                                on_delete=models.CASCADE)
    sequence_id = models.IntegerField(_("Sequence ID"))
    previous_leg = models.OneToOneField("mission.MissionLeg", verbose_name=_("Previous Leg"),
                                        null=True, blank=True,
                                        related_name='next_leg',
                                        on_delete=models.SET_NULL)

    # Departure From
    departure_location = models.ForeignKey("organisation.Organisation", verbose_name=_("Departure Location"),
                                           related_name='departure_mission_legs',
                                           on_delete=models.CASCADE)
    departure_datetime = models.DateTimeField(_("Departure Date & Time (Z)"), auto_now=False, auto_now_add=False)
    departure_sf_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Departure SFR"),
                                             related_name='departure_mission_legs',
                                             null=True, blank=True,
                                             on_delete=models.SET_NULL)
    departure_diplomatic_clearance = models.CharField(_("Departure Diplomatic Clearance"), max_length=100,
                                                      null=True, blank=True)
    departure_aml_service = models.BooleanField(_("AML Service Required?"), default=False)

    # Arrival To
    arrival_location = models.ForeignKey("organisation.Organisation", verbose_name=_("Arrival Location"),
                                         related_name='arrival_mission_legs',
                                         on_delete=models.CASCADE)
    arrival_datetime = models.DateTimeField(_("Arrival Date & Time (Z)"), auto_now=False, auto_now_add=False)
    arrival_sf_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Arrival SFR"),
                                           related_name='arrival_mission_legs',
                                           null=True, blank=True,
                                           on_delete=models.SET_NULL)
    arrival_diplomatic_clearance = models.CharField(_("Arrival Diplomatic Clearance"), max_length=100,
                                                    null=True, blank=True)
    arrival_aml_service = models.BooleanField(_("AML Service Required?"), default=False)

    pob_crew = models.IntegerField(_("POB Crew"))
    pob_pax = models.IntegerField(_("Passengers on Board"), null=True, blank=True)
    cob_lbs = models.IntegerField(_("Cargo Payload"), null=True, blank=True)
    callsign_override = models.CharField(_("Callsign"), max_length=50, null=True, blank=True)
    aircraft_type_override = models.ForeignKey("aircraft.AircraftType", verbose_name=_("Aircraft Type"),
                                               null=True,
                                               related_name='missions_flight_legs',
                                               on_delete=models.SET_NULL)
    aircraft_override = models.ForeignKey("aircraft.AircraftHistory", verbose_name=_("Tail Number"),
                                          null=True, blank=True,
                                          related_name='missions_flight_legs',
                                          on_delete=models.SET_NULL)
    air_card_prefix = models.ForeignKey("core.AirCardPrefix",
                                        verbose_name=_("AIR Card Prefix"),
                                        null=True, blank=True,
                                        on_delete=models.SET_NULL)
    air_card_number = models.IntegerField(_("AIR Card Number"), null=True, blank=True)
    air_card_expiration = models.CharField(_("AIR Card Expiration"), max_length=5, null=True, blank=True)
    air_card_photo = models.FileField(storage=AirCardPhotoStorage(), null=True, blank=True)
    is_confirmed = models.BooleanField(_("Is Confirmed?"), default=False)
    is_cancelled = models.BooleanField(_("Is Cancelled?"), default=False)
    cancellation_reason = models.ForeignKey("mission.MissionLegCancellationReason",
                                            verbose_name=_("Cancellation Reason"),
                                            null=True,
                                            related_name='legs',
                                            on_delete=models.SET_NULL)
    remarks = models.CharField(_("Remarks"), max_length=200, null=True, blank=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"),
                                   related_name='created_mission_legs',
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)

    objects = MissionLegManager().as_manager()

    # Meta flags
    meta_is_first_save = False
    meta_is_maintenance_save = False  # Signal for maintenance save (sequence update)

    class Meta:
        db_table = 'missions_legs'
        ordering = ['mission', 'sequence_id']
        app_label = 'mission'

    def __str__(self):
        return f'{self.departure_location.tiny_repr}>{self.arrival_location.tiny_repr}'

    def save(self, *args, **kwargs):
        updated_by = getattr(self, 'updated_by', None)
        self.meta_is_first_save = not self.pk  # Will be True only on first save
        mission_leg_pre_save(self)

        if not self.pk:
            setattr(self, 'is_created', True)

        super().save(*args, **kwargs)
        if not self.meta_is_maintenance_save:
            mission_leg_after_save(self)

            if not hasattr(self, 'prevent_mission_update'):
                self.mission.updated_by = updated_by
                self.mission.save()

            # Create Activity Log record for specified fields
            if not hasattr(self, 'activity_log_supress'):
                mission_leg_activity_logging(mission_leg=self)

    def validate_overlap(self):
        date_q = (
            # Inner duplicate
            (Q(departure_datetime__lte=self.departure_datetime) & Q(arrival_datetime__gte=self.arrival_datetime)) |
            # Outer duplicate
            (Q(departure_datetime__gte=self.departure_datetime) & Q(arrival_datetime__lte=self.arrival_datetime)) |
            # Is Arrival conflicts / Q(etd_date__lte=departure_date)
            (Q(departure_datetime__lte=self.departure_datetime) & Q(arrival_datetime__gte=self.departure_datetime)) |
            # Is Departure conflicts / Q(eta_date__gte=arrival_date)
            (Q(arrival_datetime__gte=self.arrival_datetime) & Q(departure_datetime__lte=self.arrival_datetime))
        )
        return self.mission.legs.filter(date_q).exclude(pk=self.pk)

    def get_callsign(self):
        return self.callsign_override if self.callsign_override else self.mission.callsign

    @property
    def aircraft_type(self):
        if self.aircraft_type_override:
            return self.aircraft_type_override
        return self.mission.aircraft_type

    @property
    def tail_number(self):
        if self.aircraft_override:
            return self.aircraft_override
        return self.mission.aircraft

    def get_pob_pax_display(self):
        if not self.pob_pax:
            return '--'
        elif self.pob_pax == 0:
            return 'TBC'
        return self.pob_pax

    def get_cob_lbs_display(self):
        if not self.cob_lbs:
            return '--'
        return self.cob_lbs

    def get_prev_leg(self):
        return getattr(self, 'previous_leg', None)

    def get_next_leg(self):
        return getattr(self, 'next_leg', None)

    @property
    def ete(self):
        duration = self.arrival_datetime - self.departure_datetime
        minutes, _ = divmod(duration.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        result = "%02d:%02d" % (hours, minutes)
        return result

    @property
    def sfr_fuel_status_badge(self):
        if not hasattr(self, 'turnaround') or not self.turnaround.handling_request:
            return None
        sfr_fuel_status = self.turnaround.handling_request.fuel_status
        return get_fuel_booking_status_circle(sfr_fuel_status['code'])

    @property
    def sfr_gh_status_badge(self):
        if not hasattr(self, 'turnaround') or not self.turnaround.handling_request:
            return None
        sfr_ground_handling_status = self.turnaround.handling_request.ground_handling_status
        return get_ground_handling_status_circle(sfr_ground_handling_status['code'])


class MissionTurnaround(models.Model):
    mission_leg = models.OneToOneField("mission.MissionLeg", verbose_name=_("Mission Leg"),
                                       related_name='turnaround', on_delete=models.CASCADE)
    fuel_required = models.ForeignKey("handling.MovementDirection", verbose_name=_("Fuel Required"),
                                      null=True, blank=True,
                                      on_delete=models.RESTRICT,
                                      db_column='fuel_required_on')
    fuel_quantity = models.PositiveBigIntegerField(_("Fuel Quantity"), null=True, blank=True)
    fuel_unit = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Fuel Unit"),
                                  limit_choices_to={'is_fluid_uom': True, },
                                  null=True, blank=True,
                                  on_delete=models.RESTRICT)
    fuel_prist_required = models.BooleanField(_("Prist Required"), default=False)
    handling_request = models.OneToOneField("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                            null=True, blank=True,
                                            related_name='mission_turnaround',
                                            on_delete=models.SET_NULL)

    def __str__(self):
        return self.mission_leg.arrival_location.tiny_repr

    class Meta:
        db_table = 'missions_legs_servicing'
        app_label = 'mission'

    def is_servicing_requested(self):
        return self.mission_leg.arrival_aml_service

    @property
    def full_repr(self):
        return 'Turnaround - {location} (Flight Legs {leg_1}/{leg_2})'.format(
            location=self.mission_leg.arrival_location.tiny_repr,
            leg_1=self.mission_leg.sequence_id,
            leg_2=self.mission_leg.next_leg.sequence_id if hasattr(self.mission_leg, 'next_leg') else '',
        )

    @property
    def sfr_url_ops(self):
        if self.handling_request:
            return reverse('admin:handling_request', args=[self.handling_request.pk])

    @property
    def sfr_url_dod(self):
        if self.handling_request:
            return reverse('dod:request', args=[self.handling_request.pk])


class MissionTurnaroundService(models.Model):
    turnaround = models.ForeignKey("mission.MissionTurnaround", verbose_name=_("MissionLegServicing"),
                                   related_name='requested_services',
                                   on_delete=models.CASCADE)
    service = models.ForeignKey("handling.HandlingService", verbose_name=_("Service"),
                                related_name='mission_turnarounds_services',
                                on_delete=models.CASCADE)
    on_arrival = models.BooleanField(_("On Arrival"), default=False)
    on_departure = models.BooleanField(_("On Departure"), default=False)
    booking_text = models.CharField(_("Details"), max_length=255, null=True, blank=True)
    booking_quantity = models.DecimalField(_("Quantity Required"),
                                           max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    booking_quantity_uom = models.ForeignKey("core.UnitOfMeasurement",
                                             verbose_name=_("Quantity Required UOM"),
                                             limit_choices_to={'is_fluid_uom': True},
                                             null=True, blank=True,
                                             on_delete=models.RESTRICT)
    note = models.CharField(_("Note"), null=True, blank=True, max_length=500)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"), null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'missions_legs_servicing_services'
        app_label = 'mission'

    def save(self, *args, **kwargs):
        if not self.pk:
            setattr(self, 'is_created', True)
            if self.booking_quantity:
                self.booking_quantity_uom = self.service.quantity_selection_uom

        super().save(*args, **kwargs)
        if hasattr(self, 'is_created'):
            self.turnaround.activity_log.create(
                author=self.updated_by,
                record_slug='mission_turnaround_service_added',
                details=f'{self.service.name}'
            )


@receiver(post_delete, sender=MissionTurnaroundService)
def mission_turnaround_service_post_delete(sender, instance, **kwargs): # noqa
    try:
        instance.turnaround.mission_turnarounds_services.get(pk=instance.pk)
        instance.turnaround.activity_log.create(
            author=getattr(instance, 'updated_by', None),
            record_slug='mission_turnaround_service_delete',
            details=f'{instance.service.name}'
        )
    except AttributeError:
        return


class MissionLegCancellationReason(models.Model):
    name = models.CharField(_("Name"), max_length=200)

    class Meta:
        db_table = 'missions_legs_cancellation_reasons'
        app_label = 'mission'
