import logging
from datetime import timedelta, datetime, date

import pytz
from cacheops import cached
from django.db import models
from django.db.models import OuterRef, Sum, F, Subquery, Case, When, BooleanField, Value, IntegerField, CharField, \
    Min, Max, ExpressionWrapper, DateTimeField, Count, Q, Exists
from django.db.models.functions import Coalesce, Concat
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.db.models.query import QuerySet
from django.utils import timezone
from shortuuidfield import ShortUUIDField
from sql_util.aggregates import SubquerySum

from app.storage_backends import AirCardPhotoStorage
from core.models import UnitOfMeasurement
from core.utils.datatables_functions import get_datatable_badge, get_fontawesome_icon
from core.utils.model_diff import ModelDiffMixin

from handling.models.amendment import HandlingRequestAmendmentSession
from handling.models.base import HandlingRequestNotificationsLog
from handling.models.sfr_payload import HandlingRequestCargoPayload
from handling.models.movement import HandlingRequestMovement
from handling.models.sfr_ops_checklist import HandlingRequestOpsChecklistItem, SfrOpsChecklistParameter
from handling.models.sfr_crew import HandlingRequestCrew
from handling.utils.activity_logging import handling_request_activity_logging

from handling.utils.amendment_session_helpers import create_amendment_session_record
from handling.utils.cache import handling_request_cache_invalidation
from handling.utils.email_diff_generator import generate_diff_dict
from handling.utils.handling_request_utils import handling_request_on_save, handling_request_amendment_notifications
from handling.utils.helpers import generate_mission_number
from handling.utils.spf_v2 import handling_request_create_or_update_spf_v2, handling_request_generate_spf_v2_pdf
from user.models import User


logger = logging.getLogger(__name__)


class HandlingRequestManager(models.Manager):
    """
    Handling Request model manager to exclude handling requests for test aircraft
    (as they by definition can't be real requests)
    """
    def get_queryset(self):
        return super().get_queryset().exclude(tail_number__aircraft__test_aircraft=True)


class HandlingRequestQuerySet(QuerySet):
    def with_status(self):
        # Status List #
        # 0 - Error status
        # 1 - In Process
        # 2 - Confirmed
        # 3 - Service Unavailable
        # 4 - Completed
        # 5 - Cancelled
        # 6 - Amended
        # 7 - Expired
        # 8 - Tail Number TBC
        # 9 - Unable to Support
        # 10 - New
        # 11 - Amended Callsign
        # 12 - AOG
        # Status List #

        is_fuel_confirmed_q = Q(
            # If fuel_required it should be confirmed
            (Q(fuel_required__isnull=False) & Q(fuel_booking__isnull=False) & Q(fuel_booking__is_confirmed=True) &
             (
                 (Q(fuel_booking__dla_contracted_fuel=False) & ~Q(fuel_booking__fuel_release='')) |
                 (Q(fuel_booking__dla_contracted_fuel=True))
             )
             ) |
            # If fuel is not required it shouldn't be confirmed
            Q(fuel_required__isnull=True)
        )

        is_services_confirmed = Q(
            (Q(services_booking_avaiting=0) & Q(services_booking_confirmed__gte=0) & Q(
                services_booking_unavailable=0)) | Q(services_requested_count=0)
            # When departure was updated after arrival and is awaiting amendment/confirmation,
            # we disregard unconfirmed departure services to maintain the Confirmed status
            | ((Exists(HandlingRequestAmendmentSession.objects.filter(
                handling_request=OuterRef('pk'), is_gh_opened=True, is_departure_update_after_arrival=True))
                | Q(is_awaiting_departure_update_confirmation=True))
               & (Q(arr_services_booking_avaiting=0) & Q(arr_services_booking_confirmed__gte=0) & Q(
                    arr_services_booking_unavailable=0) | Q(arr_services_requested_count=0)))
        )

        is_ground_handling_confirmed = Q(
            Q(is_gh_confirmation_required=True) & Q(handling_agent__isnull=False)
            & Q(is_handling_confirmed=True) & ~Exists(HandlingRequestAmendmentSession.objects.filter(
                handling_request=OuterRef('pk'), is_gh_opened=True, is_departure_update_after_arrival=False))
            | Q(is_gh_confirmation_required=False)
        )

        qs = self.annotate(
            arrival_date=Min('movement__date'),
            departure_date=Max('movement__date'),
            departure_date_plus_4h=ExpressionWrapper(
                F('departure_date') + timedelta(hours=4),
                output_field=DateTimeField()
            ),
            is_retrospective=Case(
                When(created_at__gt=F('arrival_date'), then=True),
                default=False
            ),
            retrospective_grace_period=ExpressionWrapper(
                F('created_at') + timedelta(minutes=5),
                output_field=DateTimeField()
            ),
            is_in_retrospective_grace=Case(
                When(Q(is_retrospective=True) & Q(retrospective_grace_period__gt=timezone.now()), then=True),
                default=False,
            ),
            services_requested_count=Count(
                'movement__hr_services',
            ),
            services_booking_avaiting=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed__isnull=True)
            ),
            services_booking_confirmed=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed=True)
            ),
            services_booking_unavailable=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed=False)
            ),
            arr_services_requested_count=Count(
                'movement__hr_services',
                filter=Q(movement__direction_id="ARRIVAL")
            ),
            arr_services_booking_avaiting=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed__isnull=True, movement__direction_id="ARRIVAL")
            ),
            arr_services_booking_confirmed=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed=True, movement__direction_id="ARRIVAL")
            ),
            arr_services_booking_unavailable=Count(
                'movement__hr_services',
                filter=Q(movement__hr_services__booking_confirmed=False, movement__direction_id="ARRIVAL")
            ),
            is_gh_confirmation_required=Case(
                When(airport__details__type_id=8, then=True),
                default=False,
            ),
            # TODO: Refactor this
            status=Case(
                When(
                    Q(is_aog=True),
                    then=12  # AOG
                ),
                When(
                    Q(cancelled=True),
                    then=5  # Cancelled
                ),
                When(
                    Q(is_unable_to_support=True) & Q(arrival_date__gt=timezone.now()),
                    then=9  # Unable to Support
                ),
                When(
                    (
                        Q(amended=False) &
                        Q(cancelled=False) &
                        Q(is_new=False) &
                        (is_fuel_confirmed_q & Q(services_booking_avaiting=0) & is_ground_handling_confirmed) &
                        Q(departure_date__lt=timezone.now())
                    ), then=4  # Completed
                ),
                When(
                    (
                        Q(cancelled=False) & Q(is_in_retrospective_grace=False) &
                        (
                            ~Q(is_fuel_confirmed_q) |
                            ~Q(is_services_confirmed) |
                            Q(is_handling_confirmed=False)
                        ) &
                        Q(arrival_date__lt=timezone.now())
                    ), then=7  # Expired
                ),
                When(
                    Q(is_amended_callsign=True),
                    then=11  # Amended Callsign
                ),
                When(
                    Q(cancelled=False) &
                    Q(is_new=True),
                    then=10  # New
                ),
                When(
                    (
                        Q(amended=False) &
                        is_fuel_confirmed_q &
                        is_services_confirmed & Q(departure_date__gt=timezone.now()) &
                        is_ground_handling_confirmed &
                        Q(tail_number__isnull=True) &
                        Q(departure_date__gt=timezone.now())
                    ), then=8  # Tail Number TBC
                ),
                When(
                    (
                        Q(amended=False) &
                        is_fuel_confirmed_q &
                        is_services_confirmed & Q(departure_date__gt=timezone.now()) &
                        is_ground_handling_confirmed
                    ), then=2  # Confirmed
                ),
                When(
                    (
                        Q(amended=False) &
                        (
                            # Fuel booking needed only when it's requested
                            # (Q(fuel_required__isnull=False) & Q(fuel_booking__isnull=True)) |
                            ~is_fuel_confirmed_q |
                            ~Q(is_services_confirmed) |
                            ~is_ground_handling_confirmed
                        ) &
                        (Q(departure_date__gt=timezone.now()) | Q(is_in_retrospective_grace=True))
                    ), then=1  # In Process
                ),

                When((Q(amended=False) & (Q(services_booking_avaiting=0) & Q(services_booking_unavailable__gt=0)) &
                      Q(departure_date__gt=timezone.now())), then=3),
                When(Q(amended=True), then=6),
                default=0
            ),
            is_auto_spf_available_val=Case(
                When(
                    ~Q(status__in=[7, 9, 5]) &
                    Q(handling_agent__isnull=False),
                    then=True
                ),
                default=False
            ),
        )
        return qs

    def include_payload_data(self):

        cargo_payload_sq = HandlingRequestCargoPayload.objects.filter(
            handling_request_id=OuterRef('pk'),
        ).order_by().values('handling_request_id').annotate(
            total_weight=Sum(F('weight') * F('quantity'))
        ).values('total_weight')

        qs = self.annotate(
            payload_pax_arrival=Coalesce(SubquerySum('passengers_payloads__weight', filter=Q(is_arrival=True)), 0),
            payload_pax_departure=Coalesce(SubquerySum('passengers_payloads__weight', filter=Q(is_departure=True)), 0),
            payload_pax_total=Coalesce(SubquerySum('passengers_payloads__weight'), 0),
            payload_cargo_arrival_val=Coalesce(Subquery(cargo_payload_sq.filter(is_arrival=True)), 0),
            payload_cargo_departure_val=Coalesce(Subquery(cargo_payload_sq.filter(is_departure=True)), 0),
            payload_cargo_total=F('payload_cargo_arrival_val') + F('payload_cargo_departure_val'),
            payload_arrival_total=F('payload_pax_arrival') + F('payload_cargo_arrival_val'),
            payload_departure_total=F('payload_pax_departure') + F('payload_cargo_departure_val'),
        )

        return qs

    def with_eta_etd_and_status_index(self):
        """
        Returns QuerySet with included 'eta_date', 'etd_date' and 'status_index' field
        used for sorting on S&F Requests page and API endpoint
        :return:
        """
        movement_qs = HandlingRequestMovement.objects.filter(request_id=OuterRef('pk')).values('date')

        qs = self.with_status().annotate(
            eta_date=Subquery(movement_qs.filter(direction_id='ARRIVAL')[:1]),
            etd_date=Subquery(movement_qs.filter(direction_id='DEPARTURE')[:1]),
            etd_date_grace=ExpressionWrapper(
                F('etd_date') + timedelta(hours=4),
                output_field=DateTimeField()
            ),
        )
        qs = qs.annotate(
            is_mission_expired=Case(
                When(eta_date__gt=timezone.now(), then=False),
                default=True,
                output_field=BooleanField(),
            ),
            is_departure_in_grace_period_val=Case(
                When((Q(eta_date__lt=timezone.now()) & Q(departure_date_plus_4h__gte=timezone.now())),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            status_index=Case(
                When(status=1, then=Value(30)),
                When(status=2, then=Value(40)),
                When(status=3, then=Value(30)),
                When(status=4, then=Value(50)),
                When(status=5, then=Value(60)),
                When(status=6, then=Value(20)),
                When(status=7, then=Value(70)),
                When(status=8, then=Value(40)),
                When(status=9, then=Value(55)),
                When(status=10, then=Value(10)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            is_aog_available=Case(
                When((
                    (
                        Q(status__in=[1, 2, 3, 6, 8, 10, 11]) |
                        Q(status__in=[4, ]) & Q(is_departure_in_grace_period_val=True)
                    ) &
                    Q(is_aog=False) &
                    Q(is_standalone=True)
                ), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        return qs

    def with_fuel_status(self):
        return self.annotate(
            fuel_status_val=Case(
                # Legend:
                # 0 - Error
                # 1 - No Fuel
                # 2 - No action started
                # 3 - Confirmed (No Fuel Release)
                # 4 - Confirmed (DLA Contracted Location)
                # 5 - Confirmed
                When(fuel_required__isnull=True, then=Value(1)),
                When(fuel_required__isnull=False, fuel_booking__isnull=True, then=Value(2)),
                When(fuel_required__isnull=False,
                     fuel_booking__isnull=False,
                     fuel_booking__dla_contracted_fuel=False,
                     fuel_booking__fuel_release='', then=Value(3)),
                When(fuel_required__isnull=False, fuel_booking__dla_contracted_fuel=True, then=Value(4)),
                When((Q(fuel_required__isnull=False) & Q(fuel_booking__dla_contracted_fuel=False) & ~Q(
                    fuel_booking__fuel_release='')), then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    def with_handling_status(self):
        return self.annotate(
            ground_handling_status_val=Case(
                # Legend:
                # 0 - Error
                # 1 - No action started
                # 2 - In Process
                # 3 - Confirmed
                When(handling_agent__isnull=True, then=Value(1)),
                When(handling_agent__isnull=False, is_handling_confirmed=False, then=Value(2)),
                When(handling_agent__isnull=False, is_handling_confirmed=True, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    def with_spf_v2_status(self):
        qs = self.with_eta_etd_and_status_index()
        return qs.annotate(
            spf_v2_status_val=Case(
                # Legend:
                # 0 - Error
                # 1 - Not Yet Due
                # 2 - Awaiting Reconciliation
                # 3 - Reconciled
                # 4 - Not Applicable
                When(status__in=[5, 7, 12], then=Value(4)),
                When(etd_date__gt=timezone.now(), then=Value(1)),
                When(etd_date__lt=timezone.now(), status=4, spf_v2__is_reconciled=False, then=Value(2)),
                When(etd_date__lt=timezone.now(), status=4, spf_v2__is_reconciled=True, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    def detailed_list(self, include_test_requests=False):
        qs = self.with_fuel_status().with_handling_status().with_spf_v2_status()

        if not include_test_requests:
            qs = qs.exclude(tail_number__aircraft__test_aircraft=True)

        primary_contact_qs = HandlingRequestCrew.objects.filter(
            handling_request_id=OuterRef('pk'),
            is_primary_contact=True
        ).annotate(
            first_name=Case(
                When(person__details__first_name__isnull=False, then=F('person__details__first_name')),
                default=Value(''),
                output_field=CharField(),
            ),
            last_name=Case(
                When(person__details__last_name__isnull=False, then=F('person__details__last_name')),
                default=Value(''),
                output_field=CharField(),
            )
        ).values(value=Concat(F('first_name'), Value(' '), F('last_name')))

        qs = qs.annotate(
            primary_contact_repr=Subquery(primary_contact_qs[:1]),
        )

        return qs

    def spf_to_reconcile(self):
        return self.with_eta_etd_and_status_index().filter(
            status=4,
            is_legacy_spf_v1=False,
            spf_v2__is_reconciled=False,
        )


class HandlingRequest(models.Model, ModelDiffMixin):
    objects = HandlingRequestManager.from_queryset(HandlingRequestQuerySet)()

    STATUS_DETAILS = {
        0: {'code': 0, 'detail': 'Error', 'background_color': '#fff', 'text_color': '#e11d48'},
        1: {'code': 1, 'detail': 'In Progress', 'background_color': '#e5e56b', 'text_color': '#1F2937'},
        2: {'code': 2, 'detail': 'Confirmed', 'background_color': '#10b981', 'text_color': '#fff'},
        3: {'code': 3, 'detail': 'Service Unavailable', 'background_color': '#e11d48', 'text_color': '#fff'},
        4: {'code': 4, 'detail': 'Completed', 'background_color': '#D2FFE3', 'text_color': '#374151'},
        5: {'code': 5, 'detail': 'Cancelled', 'background_color': '#111827', 'text_color': '#fff'},
        6: {'code': 6, 'detail': 'Amended', 'background_color': '#fba918', 'text_color': '#1F2937'},
        7: {'code': 7, 'detail': 'Expired', 'background_color': '#f3c78e', 'text_color': '#1F2937'},
        8: {'code': 8, 'detail': 'Confirmed (tail TBC)', 'background_color': '#10b981', 'text_color': '#fff'},
        9: {'code': 9, 'detail': 'Unable to Support', 'background_color': '#e11d48', 'text_color': '#fff'},
        10: {'code': 10, 'detail': 'NEW', 'background_color': '#1E90FF', 'text_color': '#fff'},
        11: {'code': 11, 'detail': 'Amended Callsign', 'background_color': '#fba918', 'text_color': '#1F2937'},
        12: {'code': 12, 'detail': 'AOG', 'background_color': '#e11d48', 'text_color': '#fff'},
    }

    FUEL_STATUS_DETAILS = {
        0: {'code': 0, 'color': 'black', 'background_color': '#111', 'text_color': '#ff0000', 'detail': 'Error'},
        1: {'code': 1, 'color': 'gray', 'background_color': '#10b981', 'text_color': '#374151', 'detail': 'No Fuel'},
        2: {'code': 2, 'color': 'white', 'background_color': '#f9fafb', 'text_color': '#374151',
            'detail': 'No action started'},
        3: {'code': 3, 'color': 'yellow', 'background_color': '#e5e56b', 'text_color': '#374151',
            'detail': 'Confirmed (No Fuel Release)'},
        4: {'code': 4, 'color': 'green', 'background_color': '#10b981', 'text_color': '#f9fafb',
            'detail': 'Confirmed (DLA Contracted Location)'},
        5: {'code': 5, 'color': 'green', 'background_color': '#10b981', 'text_color': '#f9fafb', 'detail': 'Confirmed'},
    }

    GROUND_HANDLING_STATUS_DETAILS = {
        0: {'code': 0, 'color': 'black', 'background_color': '#111', 'detail': 'Error'},
        1: {'code': 1, 'color': 'white', 'background_color': '#f9fafb', 'detail': 'No action started'},
        2: {'code': 2, 'color': 'yellow', 'background_color': '#e5e56b', 'detail': 'In Progress'},
        3: {'code': 3, 'color': 'green', 'background_color': '#10b981', 'detail': 'Confirmed'},
    }

    SPF_V2_STATUS_DETAILS = {
        0: {'code': 0, 'color': '#ff0000', 'background_color': '#111', 'detail': 'Error'},
        1: {'code': 1, 'color': '#374151', 'background_color': '#e5e56b', 'detail': 'Not Yet Due'},
        2: {'code': 2, 'color': '#1F2937', 'background_color': '#fba918', 'detail': 'Awaiting Reconciliation'},
        3: {'code': 3, 'color': '#374151', 'background_color': '#10b981', 'detail': 'Reconciled'},
        4: {'code': 4, 'color': '#F9FAFB', 'background_color': '#1F2937', 'detail': 'Not Applicable'},
    }

    FUEL_REQUIRED_CHOICES = (
        ("NO_FUEL", "No Fuel"),
        ("ARRIVAL", "On Arrival"),
        ("DEPARTURE", "On Departure"),
    )

    IS_PDF_AVAILABLE_STATUS_CODES = [2, 4, 8]

    type = models.ForeignKey("handling.HandlingRequestType",
                             verbose_name=_("Request Type"),
                             default=1,
                             on_delete=models.CASCADE)
    mission_number = models.CharField(_("Mission Number"), max_length=50, null=True, blank=True)
    apacs_number = models.CharField(_("Diplomatic Clearance"), max_length=50, null=True, blank=True)
    apacs_url = models.URLField(_("APACS URL"), max_length=500, null=True, blank=True)
    callsign = models.CharField(_("Callsign"), max_length=50)
    tail_number = models.ForeignKey("aircraft.AircraftHistory",
                                    verbose_name=_("Tail Number"),
                                    limit_choices_to={'details_rev__isnull': False},
                                    null=True, blank=True,
                                    on_delete=models.CASCADE)
    aircraft_type = models.ForeignKey("aircraft.AircraftType", verbose_name=_("Aircraft Type"),
                                      null=True,
                                      on_delete=models.SET_NULL)
    airport = models.ForeignKey("organisation.Organisation", verbose_name=_("Location"),
                                null=True, on_delete=models.SET_NULL,
                                related_name='airport_handling_requests')
    notify_dao = models.BooleanField(_("Notify DAO?"), default=False)
    fuel_required = models.ForeignKey("handling.MovementDirection", verbose_name=_("Fuel Required"),
                                      null=True, blank=True,
                                      choices=FUEL_REQUIRED_CHOICES,
                                      on_delete=models.RESTRICT,
                                      db_column='fuel_required_on')
    fuel_quantity = models.PositiveBigIntegerField(_("Fuel Quantity"), null=True, blank=True)
    fuel_unit = models.ForeignKey("core.UnitOfMeasurement", verbose_name=_("Fuel Unit"),
                                  limit_choices_to={'is_fluid_uom': True, },
                                  null=True, blank=True,
                                  on_delete=models.RESTRICT)
    fuel_captains_request = models.BooleanField(_("Captain's Request"), default=False)
    fuel_prist_required = models.BooleanField(_("Prist Required"), default=False)
    parking_apron = models.CharField(_("Apron"), max_length=50, null=True, blank=True)
    parking_stand = models.CharField(_("Stand"), max_length=50, null=True, blank=True)
    parking_confirmed_on_day_of_arrival = models.BooleanField(_("Parking confirmed on day of arrival"), default=False)
    handling_agent = models.ForeignKey("organisation.Organisation", verbose_name=_("Handling Agent"),
                                       limit_choices_to={'handler_details__isnull': False},
                                       null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='handler_handling_requests')
    cancelled = models.BooleanField(_("Cancelled"), default=False)
    amended = models.BooleanField(_("Amended"), default=False)
    is_standalone = models.BooleanField(_("Is Standalone"), default=True)
    is_amended_callsign = models.BooleanField(_("Callsign Amended"), default=False)
    is_new = models.BooleanField(_("New Request"), default=False)
    is_unable_to_support = models.BooleanField(_("Unable To Support?"), default=False)
    is_aog = models.BooleanField(_("AOG"), default=False)
    is_legacy_spf_v1 = models.BooleanField(_("Use Legacy SPF V1"), default=False)
    decline_reason = models.CharField(_("Decline Reason"), max_length=255, null=True)
    is_handling_confirmed = models.BooleanField(_("Handling Confirmed"), default=False)
    customer_organisation = models.ForeignKey("organisation.Organisation",
                                              verbose_name=_("Unit"),
                                              limit_choices_to={
                                                  'operator_details__isnull': False,
                                                  'operator_details__type_id__in': [13, 14, 15, 16, 17]},
                                              on_delete=models.CASCADE,
                                              related_name='handling_requests')
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"),
                                   on_delete=models.CASCADE,
                                   related_name='created_handling_requests')
    is_booking_notifications_sent = models.BooleanField(null=True)
    air_card_prefix = models.ForeignKey("core.AirCardPrefix",
                                        verbose_name=_("AIR Card Prefix"),
                                        null=True, blank=True,
                                        on_delete=models.CASCADE)
    air_card_number = models.IntegerField(_("AIR Card Number"), null=True, blank=True)
    air_card_expiration = models.CharField(_("AIR Card Expiration"), max_length=5, null=True, blank=True)
    air_card_photo = models.FileField(storage=AirCardPhotoStorage(), null=True, blank=True)
    crew = models.ManyToManyField("user.Person", verbose_name='Crew', blank=False, related_name='missions',
                                  through='HandlingRequestCrew')
    assigned_mil_team_member = models.ForeignKey("user.Person", verbose_name=_("Assigned Mil Team Member"),
                                                 related_name='assigned_handling_requests',
                                                 null=True, blank=True,
                                                 limit_choices_to={'user__roles': 1000},
                                                 on_delete=models.CASCADE)
    is_awaiting_departure_update_confirmation = models.BooleanField(_("Is Awaiting Departure Update Confirmation?"),
                                                                    default=False)
    uuid = ShortUUIDField(auto=True, editable=False)

    # Meta tags
    amendment_fields = {'callsign', 'airport_id', 'tail_number_id', 'aircraft_type_id', 'fuel_required_id',
                        'fuel_quantity', 'fuel_unit_id'}
    fuel_amendment_fields = {'fuel_required_id', 'fuel_quantity', 'fuel_unit_id', 'fuel_prist_required'}
    supress_amendment_notifications = False
    is_services_amended = False
    is_movement_amended = False
    is_fuel_related_data_amended = False
    meta_is_first_save = None
    meta_creation_source = None

    class Meta:
        db_table = 'handling_requests'
        ordering = ['-created_at']
        app_label = 'handling'

    def __str__(self):
        return f'{self.id}'

    def save(self, *args, **kwargs):
        if settings.DEBUG:
            logger.warning(f'S&F Request {self.pk}: Saving...')
        updated_by = getattr(self, 'updated_by', None)
        self.meta_is_first_save = not self.pk  # Will be True only on first save
        old_instance_diff = getattr(self, 'old_instance_diff', None)
        # Remove spaces from callsign and force it to uppercase
        self.callsign = self.callsign.replace(" ", "").upper()

        if not self.is_standalone:
            self.meta_creation_source = 'Mission'

        if self.pk:
            if not hasattr(self, 'confirm_tail_number_action'):
                # Amendment Session for the GH Amendment Email
                fields_to_save_in_amendment_session = ['callsign', 'tail_number_id', 'aircraft_type_id', ]
                if set(fields_to_save_in_amendment_session).intersection(self.changed_fields):
                    create_amendment_session_record(self)

                if not hasattr(self, 'is_created'):
                    handling_request_on_save(self)

                    if not old_instance_diff:
                        old_instance = HandlingRequest.objects.filter(pk=self.pk).first()
                        if old_instance:
                            old_instance_diff = generate_diff_dict(handling_request=old_instance)

        if not self.pk:
            self.is_new = True
            setattr(self, 'is_created', True)

            # Suppress fuel details in case when no fuel required
            if not self.fuel_required:
                self.fuel_quantity = None
                self.fuel_unit = None
                self.fuel_prist_required = False

            if self.parking_confirmed_on_day_of_arrival is False:
                self.parking_apron = None
                self.parking_stand = None

            # Set preferred Ground Handler if it has not picked by user
            if not self.handling_agent:
                preferred_handler_row = self.customer_organisation.operator_preferred_handlers.filter(
                    location=self.airport).first()
                if preferred_handler_row:
                    self.handling_agent = preferred_handler_row.ground_handler

            self.mission_number = generate_mission_number(self)

            # Prepare checklist items to be created for newly created S&F request
            self.new_checklist_items = []
            template_items = SfrOpsChecklistParameter.objects.filter(
                Q(location__isnull=True) | Q(location=self.airport), is_active=True)

            for item in template_items:
                self.new_checklist_items.append(HandlingRequestOpsChecklistItem(
                    request=self,
                    checklist_item=item
                ))

        super().save(*args, **kwargs)

        # Create or update SPF V2
        if 'handling_agent_id' in self.changed_fields or self.is_movement_amended or self.is_services_amended:
            handling_request_create_or_update_spf_v2(self)

        # Save new checklist items (if any)
        if getattr(self, 'new_checklist_items', None):
            HandlingRequestOpsChecklistItem.objects.bulk_create(self.new_checklist_items)
            self.new_checklist_items = None

        # Create Activity Log record for specified fields
        if not hasattr(self, 'activity_log_supress'):
            handling_request_activity_logging(handling_request=self, author=updated_by)

        if not hasattr(self, 'is_created') and not self.supress_amendment_notifications:
            # Process amendment
            if old_instance_diff:
                if not hasattr(self, 'supress_amendment'):
                    handling_request_amendment_notifications(handling_request=self, old_instance_diff=old_instance_diff)

            # Update Statuses
            self.invalidate_cache()
            if not self.is_standalone and hasattr(self, 'mission_turnaround'):
                from mission.utils.mission_utils import calculate_mission_status_flags
                calculate_mission_status_flags(self.mission_turnaround.mission_leg.mission)

    def get_absolute_url(self):
        return reverse('admin:handling_request', args=[str(self.id)])

    def invalidate_cache(self):
        self.get_fuel_status.invalidate(self)
        self.get_ground_handling_status.invalidate(self)
        self.get_spf_v2_status.invalidate(self)

        handling_request_cache_invalidation(self)

    @property
    def reference(self):
        return f'AML-DoD-{self.pk}'

    @property
    def location_tiny_repr(self):
        if self.airport.details.type_id == 8:
            return self.airport.airport_details.icao_code
        else:
            return self.airport.full_repr

    @property
    def location_short_repr(self):
        if self.airport.details.type_id == 8:
            return self.airport.airport_details.icao_iata
        else:
            return self.airport.full_repr

    @property
    def location_country(self):
        if self.airport.details.type_id == 8:
            return self.airport.airport_details.region.country
        else:
            return self.airport.details.country

    @property
    def localised_fuel_unit(self):
        if self.location_country.code == 'US':
            return UnitOfMeasurement.objects.filter(pk=1).first()
        else:
            return UnitOfMeasurement.objects.filter(pk=2).first()

    @cached_property
    def localised_fuel_details(self):
        fuel_quantity = self.fuel_quantity
        source_fuel_unit = self.fuel_unit
        target_fuel_unit = self.localised_fuel_unit
        uom_litre = UnitOfMeasurement.objects.filter(pk=2).first()

        if source_fuel_unit != target_fuel_unit:
            conversion_method = source_fuel_unit.conversion_from_methods.filter(
                (Q(specific_fuel_id=1) | Q(specific_fuel_id=None)),
                uom_converting_to=target_fuel_unit,
            ).first()

            # Convert and return values if conversion method found
            if conversion_method:
                fuel_quantity = fuel_quantity / conversion_method.conversion_ratio_div
                return fuel_quantity, target_fuel_unit
            else:
                # Fallback conversion through litres
                conversion_method_to_litre = source_fuel_unit.conversion_from_methods.filter(
                    (Q(specific_fuel_id=1) | Q(specific_fuel_id=None)),
                    uom_converting_to=2,
                ).first()

                # Convert fuel quantity to litres
                if conversion_method_to_litre:
                    fuel_quantity_litres = fuel_quantity / conversion_method_to_litre.conversion_ratio_div

                    # Find DIRECT conversion method from litres to %target_fuel_unit%
                    conversion_method_from_litre = uom_litre.conversion_from_methods.filter(
                        (Q(specific_fuel_id=1) | Q(specific_fuel_id=None)),
                        uom_converting_to=target_fuel_unit,
                    ).first()

                    if conversion_method_from_litre:
                        fuel_quantity = fuel_quantity_litres / conversion_method_from_litre.conversion_ratio_div
                        return fuel_quantity, target_fuel_unit
                    # else:
                    #     # Find REVERSE conversion method for litres
                    #     conversion_method_from_litre = uom_litre.conversion_to_methods.filter(
                    #         (Q(specific_fuel_id=1) | Q(specific_fuel_id=None)),
                    #         uom_converting_from=target_fuel_unit,
                    #     ).first()
                    #     if conversion_method_from_litre:
                    #         fuel_quantity = fuel_quantity_litres / conversion_method_from_litre.conversion_ratio_div
                    #         return fuel_quantity, target_fuel_unit

        # Return source values in case if conversion not happened
        return fuel_quantity, source_fuel_unit

    @cached_property
    def primary_contact(self):
        """
        Return Primary Mission Contact
        :return: Person object
        """
        primary_contact = self.mission_crew.filter(is_primary_contact=True).first()
        return primary_contact.person if primary_contact else None

    @property
    def crew_users(self):
        """
        Returns all Handling Request crew members
        :return: QuerySet
        """
        return User.objects.filter(person__sfr_crews__handling_request=self)

    @property
    def crew_manager_users(self):
        """
        Returns Handling Request crew members who can update SFR
        :return: QuerySet
        """
        return User.objects.filter(
            (Q(person__sfr_crews__can_update_mission=True) | Q(person__sfr_crews__is_primary_contact=True)),
            person__sfr_crews__handling_request=self,
        )

    def get_eta_date(self):
        return getattr(self, 'eta_date', self.arrival_movement.date)

    def get_etd_date(self):
        return getattr(self, 'etd_date', self.departure_movement.date)

    @cached_property
    def ete_minutes(self):
        eta_date = self.get_eta_date()
        etd_date = self.get_etd_date()

        duration = etd_date - eta_date
        minutes, _ = divmod(duration.total_seconds(), 60)
        return minutes

    @cached_property
    def is_spf_v2_editable(self):
        status_code = self.get_full_status['code']
        return all([
            status_code == 4,
            not self.spf_v2.is_reconciled,
        ])

    @property
    def passengers_count(self):
        return self.movement.aggregate(max_passengers=Max('passengers'))['max_passengers']

    @property
    def payload_cargo_arrival(self):
        return getattr(self, 'payload_cargo_arrival_val',
                       HandlingRequest.objects.include_payload_data().get(pk=self.pk).payload_cargo_arrival_val)

    @property
    def payload_cargo_departure(self):
        return getattr(self, 'payload_cargo_departure_val',
                       HandlingRequest.objects.include_payload_data().get(pk=self.pk).payload_cargo_departure_val)

    @property
    # Do not cache this property
    def is_pax_on_board(self):
        return self.movement.filter(is_passengers_onboard=True).exists()

    @cached_property
    # Do not cache this property
    def is_cargo_on_board(self):
        return False

    @cached_property
    def get_status(self):
        status = getattr(self, 'status', None)

        if not status:
            handling_request = HandlingRequest.objects.with_status().get(pk=self.pk)
            status = getattr(handling_request, 'status', None)

        return status

    @property
    def is_cancelable(self):
        return self.get_status not in (4, 5, 7, 9)

    @cached_property
    def is_admin_edit_available(self):
        """
        Allow "Admin Edit" functionality in cases:
         - Status in "Confirmed" or "Confirmed (Tail TBC)" and ETA is passed
         - Status is "Expired"
         - Status is "Completed"
        :return: Boolean value
        """
        status_code = self.get_status
        return any([
            status_code in [2, 8] and self.get_eta_date() < timezone.now(),
            status_code in [4, 7],
        ])

    @property
    def is_cancelable_grace_period(self):
        return self.get_status == 4 and self.departure_movement.date + timedelta(hours=24) >= timezone.now()

    @property
    def is_expired(self):
        if hasattr(self, 'is_mission_expired'):
            return self.is_mission_expired
        return not self.movement.filter(direction="ARRIVAL", date__gt=timezone.now()).exists()

    @property
    def is_urgent(self):
        """
        Is S&F Request in "urgent" period (less than 48 hours until arrival)
        :return:
        """
        arrival_date = self.arrival_movement.date
        date_48h_before = arrival_date - timedelta(hours=48)
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)

        return date_48h_before <= now <= arrival_date

    @property
    def is_pdf_available(self):
        """
        Return value is S&F Request Details PDF file available to download
        :return: bool
        """
        status_code = getattr(self, 'status', 0)
        return status_code in self.IS_PDF_AVAILABLE_STATUS_CODES

    @property
    def is_auto_spf_available(self):
        if hasattr(self, 'is_auto_spf_available_val'):
            return self.is_auto_spf_available_val

    def get_spf_pdf(self, save_pdf=False):
        if self.is_legacy_spf_v1:
            from handling.utils.spf_auto import generate_auto_spf
            return generate_auto_spf(self, save_pdf)
        else:
            return handling_request_generate_spf_v2_pdf(self, save_pdf)

    @property
    def is_departure_editing_grace_period(self):
        """
        Returns True if S&F Request in "departure movement editing grace period"
        "Grace Period" = After 'arrival.date' and until 'departure.date + 4 hours'
        :return: bool
        """
        handling_request = self
        arrival_movement = getattr(handling_request, 'arrival_movement', None)
        departure_movement = getattr(handling_request, 'departure_movement', None)

        if arrival_movement and departure_movement:
            departure_date_plus_4h = departure_movement.date + timedelta(hours=4)

            return all([arrival_movement.date < timezone.now(),
                        timezone.now() <= departure_date_plus_4h,
                        ])

        return None

    @property
    def is_ground_handling_confirmation_applicable(self):
        return self.airport.details.type_id == 8

    @property
    def is_ground_handling_request_can_be_sent(self):
        """
        This property indicate is S&F Request ready to send GH Request email message
        :return:
        """
        if self.airport.details.type_id == 1002:
            return False
        return True

    @property
    def is_ground_handling_can_be_cancelled(self):
        # Allow GH cancellation in case if Ground Handler has been changed or S&F Request cancelled
        if hasattr(self, 'auto_spf') and self.auto_spf.sent_to:
            if self.auto_spf.sent_to != self.handling_agent:
                return True
            if self.cancelled:
                return True
        return False

    @cached_property
    def is_gh_signed_spf_request_can_be_sent(self):
        return all([
            self.get_status == 4,
            self.notifications.is_spf_gh_request_email_sent is False,
            not self.documents.filter(pk=3).exists()
        ])

    @property
    def is_details_editable(self):
        if not self.is_standalone:
            return False
        return True

    @property
    def is_arrival_movement_editable(self):
        if not self.is_standalone:
            return False

        if hasattr(self, 'eta_date'):
            return self.eta_date > timezone.now()

        movement = getattr(self, 'arrival_movement', None)
        if movement:
            return movement.date > timezone.now()

    @property
    def is_departure_movement_editable(self):
        if not self.is_standalone:
            return False

        if hasattr(self, 'etd_date'):
            departure_date = self.etd_date
        else:
            movement = getattr(self, 'departure_movement', None)
            departure_date = movement.date

        return any([departure_date > timezone.now(), self.is_departure_editing_grace_period])

    def is_request_editable(self, user=None):
        status_code = self.get_full_status['code']
        if user and user.is_superuser:

            is_in_retrospective_grace = getattr(self, 'is_in_retrospective_grace', False)
            if is_in_retrospective_grace:
                return True

            if status_code not in (4, 5, 7, 9):
                return True
        else:
            if status_code not in (4, 5, 7, 9):
                return True

        return False

    @property
    def is_services_editable(self):
        """
        Property returns True in cases when S&F Request details can be edited
        Despite name used in various cases.
        :return: bool
        """
        if not hasattr(self, 'status'):
            instance = HandlingRequest.objects.with_status().get(pk=self.pk)
        else:
            instance = self

        if getattr(self, 'is_in_retrospective_grace', False):
            return True

        return all(
            (
                not self.is_expired,
                instance.status not in (4, 5, 7, 9),
            )
        )

    @property
    def is_departure_services_editable(self):
        """
        A special case of is_services_editable, used to determine whether 'Send Departure Update to GH' btn is enabled;
        In some cases edition of the departure movement after arrival adds new services, and we want to process those.
        Essentially, we are simply ignoring the arrival time and checking only the overall status.
        :return: bool
        """
        return self.get_status not in (4, 5, 7, 9)

    @cached_property
    def get_full_status(self):
        status_code = getattr(self, 'status', None)
        if not status_code:
            status_code = HandlingRequest.objects.with_status().get(pk=self.pk).status
        return self.STATUS_DETAILS[status_code]

    def get_status_badge(self):
        status_code = getattr(self, 'status', 0)
        status_html = get_datatable_badge(
            badge_text=self.STATUS_DETAILS[status_code]['detail'],
            badge_class=f'hr_status_{status_code} datatable-badge-normal me-1',
        )
        return status_html

    def get_spf_status_badge(self):
        spf_status = getattr(self, 'spf_status', None)
        spf_status_html = ''
        if spf_status and spf_status['code'] in (1, 2):
            if spf_status['code'] == 1:
                spf_status_html = get_datatable_badge(badge_text='SPF',
                                                      badge_class='datatable-badge-normal me-1 bg-danger')
            if spf_status['code'] == 2:
                spf_status_html = get_datatable_badge(badge_text='SPF',
                                                      badge_class='datatable-badge-normal me-1 bg-success')
        return spf_status_html

    def get_recurrence_group_badge(self):
        recurring_request_html = ''
        if self.recurrence_groups_membership.exists():
            recurring_request_html = get_fontawesome_icon(icon_name='redo',
                                                          tooltip_text='This S&F Request is a part of recurrence group')
        return recurring_request_html

    @cached(timeout=15768000)
    def get_fuel_status(self):
        if hasattr(self, 'fuel_status_val'):
            return self.fuel_status_val
        sfr = HandlingRequest.objects.with_fuel_status().get(pk=self.pk)
        return sfr.fuel_status_val

    @property
    def fuel_status(self):
        return self.FUEL_STATUS_DETAILS[self.get_fuel_status()]

    @cached(timeout=15768000)
    def get_ground_handling_status(self):
        if hasattr(self, 'ground_handling_status_val'):
            return self.ground_handling_status_val
        sfr = HandlingRequest.objects.with_handling_status().get(pk=self.pk)
        return sfr.ground_handling_status_val

    @property
    def ground_handling_status(self):
        return self.GROUND_HANDLING_STATUS_DETAILS[self.get_ground_handling_status()]

    @cached(timeout=15768000)
    def get_spf_v2_status(self):
        if hasattr(self, 'spf_v2_status_val'):
            return self.spf_v2_status_val
        sfr = HandlingRequest.objects.with_spf_v2_status().get(pk=self.pk)
        return sfr.spf_v2_status_val

    def spf_v2_status(self):
        return self.SPF_V2_STATUS_DETAILS[self.get_spf_v2_status()]

    @property
    def arrival_movement(self):
        return self.movement.filter(direction="ARRIVAL").first()

    @property
    def departure_movement(self):
        return self.movement.filter(direction="DEPARTURE").first()

    @property
    def fuel_required_date(self):
        movement = self.movement.filter(direction=self.fuel_required).first()
        if movement:
            return movement.date
        return None

    @property
    def is_ppr_number_set(self):
        return self.movement.filter(ppr_number__isnull=False).exists()

    @property
    def booking_completed(self):
        """
        Return True once all required booking confirmation actions has been satisfied
        Primarily used for push notifications
        :return:
        """
        if not hasattr(self, 'services_booking_avaiting'):
            from handling.models.movement import HandlingRequestServices
            self.services_booking_avaiting = HandlingRequestServices.objects.filter(
                booking_confirmed__isnull=True).count()

        if (self.services_booking_avaiting == 0 and
                (self.fuel_required and hasattr(self, 'fuel_booking') and
                 self.fuel_booking.is_confirmed or not self.fuel_required)):
            return True
        else:
            return False

    @property
    def is_fuel_booking_confirmed(self):
        """Function that return legacy boolean value for the fuel booking status"""
        if not self.fuel_required:
            return True
        fuel_status = self.get_fuel_status()
        return fuel_status in [3, 4, 5]

    @property
    def tail_number_changed(self):
        from handling.models.movement import HandlingRequestServices
        tail_number_amendment_record = self.activity_log.filter(
            record_slug='sfr_tail_number_id_amendment').order_by('created_at').last()
        if tail_number_amendment_record:
            return HandlingRequestServices.objects.filter(
                movement__request=self,
                booking_confirmed=False,
                updated_at__lt=tail_number_amendment_record.created_at
            ).exists()
        else:
            return False

    @property
    def spf_status(self):
        spf_bool = hasattr(self, 'spf')
        status = getattr(self, 'status')

        if status == 4 and not spf_bool:
            status_code = 1
            status_text = 'Not Submitted'
        elif status == 4 and spf_bool:
            status_code = 2
            status_text = 'Submitted'
        else:
            status_code = 0
            status_text = 'Not Yet Due'

        spf_status = {'code': status_code, 'detail': status_text}
        return spf_status

    @property
    def fuel_dla_contract(self):
        """
        Returns first valid "Fuel DLA Contract" for the S&F Request location
        :return: DLAContractLocation object
        """
        contracted_locations_qs = self.airport.dla_contracted_locations_here.filter(
            is_active=True,
            start_date__lte=self.arrival_movement.date,
            end_date__gte=self.arrival_movement.date,
        ).exclude(
            supplier__details__type_id=1000,
        )

        return contracted_locations_qs.first()

    @property
    def fuel_required_full_repr(self):
        if not self.fuel_required:
            return 'No Fuel'
        else:
            return f'{self.fuel_quantity} {self.fuel_unit} ({self.fuel_required.name})'

    @cached_property
    def opened_gh_amendment_session(self):
        return self.amendment_sessions.filter(is_gh_opened=True).first()

    @property
    def aircraft_mtow_override_kg_text(self):
        organisation_aircraft_type = self.customer_organisation.organisation_aircrafts.filter(
            aircraft_type=self.aircraft_type,
        ).first()
        if organisation_aircraft_type and organisation_aircraft_type.mtow_override_kg:
            return f'{organisation_aircraft_type.mtow_override_kg} kg'
        if self.aircraft_type.mtow_indicative_kg:
            return f'{self.aircraft_type.mtow_indicative_kg} kg'
        return 'TBC'

    @property
    def aircraft_mtow_override_lbs_text(self):
        organisation_aircraft_type = self.customer_organisation.organisation_aircrafts.filter(
            aircraft_type=self.aircraft_type,
        ).first()
        if organisation_aircraft_type and organisation_aircraft_type.mtow_override_lbs:
            return f'{organisation_aircraft_type.mtow_override_lbs} lbs'
        if self.aircraft_type.mtow_indicative_lbs:
            return f'{self.aircraft_type.mtow_indicative_lbs} lbs'
        return 'TBC'

    def reset_handler_parking_confirmation_state(self):
        if hasattr(self, 'notifications'):
            notifications = self.notifications
            notifications.is_handler_parking_confirmation_email_sent = False
            notifications.save()

    @property
    def ops_checklist_outstanding_items_icon(self):
        checklist_items = self.sfr_ops_checklist_items.all()
        completed_items = list(filter(lambda item: item.is_completed, checklist_items))

        if checklist_items and len(completed_items) < len(checklist_items):
            return get_fontawesome_icon(
                icon_name='exclamation-triangle',
                tooltip_text=self.ops_checklist_outstanding_items_str,
                margin_class='',
                additional_classes='text-warning nested-tooltip-icon',
                tooltip_enable_html=True,
            )
        else:
            return ''

    @property
    def ops_checklist_outstanding_items_str(self):
        checklist_items = self.sfr_ops_checklist_items.all()
        outstanding_items = list(filter(lambda item: not item.is_completed, checklist_items))

        if outstanding_items:
            result_str = f"Outstanding Items:<br><br><ul>"\
                         f"{''.join([f'<li>{item}</li>' for item in outstanding_items])}</ul>"

            return result_str

    @property
    def ops_checklist_status_badge(self):
        checklist_items = self.sfr_ops_checklist_items.all()
        completed_items = list(filter(lambda item: item.is_completed, checklist_items))

        if not checklist_items:
            return ''
        elif len(completed_items) < len(checklist_items):
            badge_text = f'{len(completed_items)} / {len(checklist_items)}'
            badge_color_class = 'hr_status_4'
        else:
            badge_text = 'Complete'
            badge_color_class = 'hr_status_2'

        return get_datatable_badge(
            badge_text=badge_text,
            badge_class=f'{badge_color_class} ops-checklist-status-badge datatable-badge-normal my-auto me-1',
        )

    @cached_property
    def enforce_fuel_order_note(self):
        today = date.today()
        location_contracts_to_enforce = list(self.airport.dla_contracted_locations_here.filter(
            Q(start_date__lte=today) & Q(end_date__gte=today)
            & Q(Q(early_termination_date__gte=today) | Q(early_termination_date__isnull=True))
            & Q(is_active=True), Q(enforce_fuel_order=True)))

        if not location_contracts_to_enforce:
            return None
        elif any(filter(lambda x: x.supplier_id == 100000000, location_contracts_to_enforce)):
            return "This is an AML-DLA contracted location, but please set up fuel regardless to notify our supplier."
        else:
            return "This is a NON AML-DLA contracted location, but please set up fuel regardless."




@receiver(post_save, sender=HandlingRequest)
def handling_request_submission_notifications(sender, instance, created, **kwargs): # noqa
    logger.info('S&F Request (post_save)')
    if not hasattr(instance, 'skip_signal'):
        if created:
            logger.info('S&F Request (post_save): created')
            # Create "Notifications Log" record
            HandlingRequestNotificationsLog.objects.get_or_create(handling_request=instance)
            # Send "DoD Fuel Order" email to the fuel team
            from ..tasks import handling_request_send_fuel_team_booking_invite
            handling_request_send_fuel_team_booking_invite.apply_async(args=(instance.id,), countdown=2)
            if instance.is_standalone:
                # Send "New Servicing & Fueling Request" staff email
                from ..tasks import handling_request_submitted_staff_notification
                handling_request_submitted_staff_notification.apply_async(args=(instance.id,), countdown=2)


@receiver(post_save, sender=HandlingRequest)
def handling_request_notify_dao(sender, instance, created, **kwargs): # noqa
    """Send "Notify DAO" email message if handling request notify_dao=True"""
    if not hasattr(instance, 'skip_signal'):
        if created and instance.notify_dao is True:
            from ..tasks import handling_request_notify_dao
            handling_request_notify_dao.delay(instance.id)
