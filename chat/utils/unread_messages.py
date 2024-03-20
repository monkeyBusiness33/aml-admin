from django.db.models import Q

from chat.models import Message


def get_person_unread_messages_count(person):
    qs = Message.objects.filter(
        (Q(conversation__people=person) | Q(conversation__handling_request__crew=person)),
        (~Q(author=person) & ~Q(seen_by=person)),
    ).distinct()
    unread_messages_count = qs.count()
    return unread_messages_count
