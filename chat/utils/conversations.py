from channels.layers import get_channel_layer

from chat.consumers import send_conversation_details_update
from chat.models import Conversation
from user.models import Person


channel_layer = get_channel_layer()


def handling_request_create_conversation(handling_request, author):
    conversation, created = Conversation.objects.get_or_create(
        handling_request=handling_request
    )

    if not created:
        return conversation

    handling_request_people = list(handling_request.crew.all())
    handling_request_people.append(author)

    # Invite assigned Mil Team Member
    if handling_request.assigned_mil_team_member:
        handling_request_people.append(handling_request.assigned_mil_team_member)
    conversation.people.add(*handling_request_people, through_defaults={})

    # Invite all Mil Team
    mil_team_people = Person.objects.filter(user__roles__id=1000)
    conversation.people.add(*mil_team_people, through_defaults={})

    # Send conversation update for all involved users
    send_conversation_details_update(channel_layer=channel_layer,
                                     conversation=conversation,
                                     people=conversation.people.all())

    handling_request.activity_log.create(
        record_slug='sfr_chat_conversation_created',
        author=author,
        details='Created Conversation',
    )
    return conversation


def mission_create_conversation(mission, author):
    conversation, created = Conversation.objects.get_or_create(
        mission=mission
    )

    if not created:
        return conversation

    mission_people = [author, ]

    # Invite assigned Mil Team Member
    if mission.assigned_mil_team_member:
        mission_people.append(mission.assigned_mil_team_member)

    if mission.requesting_person:
        mission_people.append(mission.requesting_person)

    conversation.people.add(*mission_people, through_defaults={})

    # Invite all Mil Team
    mil_team_people = Person.objects.filter(user__roles__id=1000)
    conversation.people.add(*mil_team_people, through_defaults={})

    # Send conversation update for all involved users
    send_conversation_details_update(channel_layer=channel_layer,
                                     conversation=conversation,
                                     people=conversation.people.all())

    mission.activity_log.create(
        details='Created Conversation',
        author=author,
    )

    return conversation
