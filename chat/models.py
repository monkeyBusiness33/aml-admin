from django.db.models import Q, OuterRef, Subquery
from shortuuidfield import ShortUUIDField

from django.utils.translation import gettext_lazy as _
from django.db import models
from sql_util.aggregates import Exists

from handling.models import HandlingRequestMovement
from mission.models import MissionLeg


class ConversationManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        sfr_movement_qs = HandlingRequestMovement.objects.filter(
            request_id=OuterRef('handling_request_id')).values('date')
        mission_leg_sq = MissionLeg.objects.filter(mission_id=OuterRef('mission_id'))

        qs = qs.annotate(
            sfr_eta_date=Subquery(sfr_movement_qs.filter(direction_id='ARRIVAL')[:1]),
            sfr_etd_date=Subquery(sfr_movement_qs.filter(direction_id='DEPARTURE')[:1]),
            mission_start_date=Subquery(
                mission_leg_sq.filter(previous_leg__isnull=True).values('departure_datetime')[:1]),
            mission_end_date=Subquery(mission_leg_sq.filter(next_leg__isnull=True).values('arrival_datetime')[:1]),
        )
        return qs

    def get_person_conversations(self, person):
        if not person.user.is_staff:
            return self.filter(
                Q(people=person) |
                Q(handling_request__crew=person) |
                Q(handling_request__customer_organisation__in=person.organisation_people.values_list(
                    'organisation_id', flat=True)) |
                Q(mission__requesting_person=person) |
                Q(mission__crew=person) |
                Q(mission__organisation__in=person.organisation_people.values_list(
                    'organisation_id', flat=True))
            ).distinct()

        return self


class Conversation(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=128, default='')
    people = models.ManyToManyField("user.Person", verbose_name='People',
                                    blank=True,
                                    related_name='chat_conversations',
                                    through='chat.ConversationPeople')
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         related_name='chat_conversations',
                                         null=True, blank=True,
                                         on_delete=models.CASCADE)
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                null=True, blank=True,
                                related_name='chat_conversations',
                                on_delete=models.CASCADE)

    objects = ConversationManager()

    class Meta:
        db_table = 'chat_conversations'

    def __str__(self):
        return f"{self.id}"

    @property
    def online_people(self):
        return self.people.filter(chat_online__person__chat_conversations=self)

    def get_name(self):
        if self.handling_request_id:
            if hasattr(self, 'sfr_eta_date'):
                sfr_eta_date = self.sfr_eta_date.strftime("%b-%d").upper() if self.sfr_eta_date else ''
            else:
                sfr_eta_date = self.handling_request.arrival_movement.date.strftime("%b-%d").upper()

            if hasattr(self, 'sfr_etd_date'):
                sfr_etd_date = self.sfr_etd_date.strftime("%b-%d").upper() if self.sfr_etd_date else ''
            else:
                sfr_etd_date = self.handling_request.departure_movement.date.strftime("%b-%d").upper()

            name = '{callsign} - {icao_code} - {arrival_date} / {departure_date}'.format(
                callsign=self.handling_request.callsign,
                icao_code=self.handling_request.location_tiny_repr,
                arrival_date=sfr_eta_date,
                departure_date=sfr_etd_date,
            )
            return name

        if self.mission:
            mission_start_date = ''
            mission_end_date = ''
            if hasattr(self, 'mission_start_date'):
                mission_start_date = self.mission_start_date.strftime("%b-%d").upper()
            if hasattr(self, 'mission_end_date'):
                mission_end_date = self.mission_end_date.strftime("%b-%d").upper()

            name = '{mission_number} / {callsign} / {start_date} / {end_date}'.format(
                mission_number=self.mission.mission_number_repr,
                callsign=self.mission.callsign,
                start_date=mission_start_date,
                end_date=mission_end_date,
            )
            return name
        return self.name


class ConversationPeople(models.Model):
    person = models.ForeignKey("user.Person", on_delete=models.CASCADE)
    conversation = models.ForeignKey("chat.Conversation", on_delete=models.CASCADE)

    class Meta:
        db_table = 'chat_conversations_people'


class MessageManager(models.Manager):
    def with_details(self):
        qs = self.annotate(
            is_read_annotated=Exists('seen_by', filter=~Q(person_id=OuterRef('author_id')))
        )
        return qs


class Message(models.Model):
    id = ShortUUIDField(primary_key=True, editable=False)
    conversation = models.ForeignKey("chat.Conversation", on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey("user.Person", on_delete=models.CASCADE, related_name="chat_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    seen_by = models.ManyToManyField("user.Person", verbose_name='Seen By',
                                     blank=True, related_name='chat_seen_messages',
                                     through='chat.MessageSeenBy')

    objects = MessageManager()

    def __str__(self):
        return f"[{self.timestamp}]: {self.id}"

    class Meta:
        db_table = 'chat_messages'
        ordering = ['-timestamp', ]


class MessageSeenBy(models.Model):
    person = models.ForeignKey("user.Person", on_delete=models.CASCADE)
    message = models.ForeignKey("chat.Message", on_delete=models.CASCADE)

    class Meta:
        db_table = 'chat_messages_seen'


class PeopleOnline(models.Model):
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='chat_online',
                               on_delete=models.CASCADE)
    channel_name = models.CharField(_("Channel Name"), max_length=100, null=True)

    class Meta:
        db_table = 'chat_online_people'

    def __str__(self):
        return f"{self.person_id}"
