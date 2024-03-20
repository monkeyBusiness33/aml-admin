from ajax_datatable import AjaxDatatableView
from django.db.models import Q
from django.views.generic import FormView
from django.contrib import messages

from notifications.signals import notify

from administration.forms.broadcast_message import SendBroadcastMessageForm
from core.models.activity_log import ActivityLog
from core.tasks import send_push
from core.utils.datatables_functions import get_datatable_clipped_value
from user.mixins import AdminPermissionsMixin
from user.models import User


class SendBroadcastMessageView(AdminPermissionsMixin, FormView):
    template_name = 'broadcast_message.html'
    form_class = SendBroadcastMessageForm
    permission_required = ['administration.p_send_broadcast_message']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_valid(self, form, *args, **kwargs):
        request_person = getattr(self.request.user, 'person')
        send_to = form.cleaned_data['send_to']
        send_via = form.cleaned_data['send_via']
        message_title = form.cleaned_data['title']
        message_text = form.cleaned_data['text']

        send_to_q = Q()
        if send_to == 'all_users':
            send_to_q = Q()
        elif send_to == 'staff':
            send_to_q = Q(is_staff=True)
        elif send_to == 'clients':
            send_to_q = Q(is_staff=False)

        users_to_send = User.objects.filter(send_to_q).distinct()

        for method in send_via:
            if method == 'push':
                send_push.delay(
                    title=message_title,
                    body=message_text,
                    users=list(users_to_send.filter(fcmdevice__isnull=False).distinct().values_list('pk', flat=True)),
                )

            if method == 'web':
                notify.send(request_person,
                            recipient=users_to_send,
                            verb=message_title,
                            description=message_text,
                            )

        data = {
            'title': message_title,
            'text': message_text,
            'sent_via': send_via,
            'sent_to': send_to,
        }

        ActivityLog.objects.create(
            author=request_person,
            record_slug='broadcast_message',
            data=data,
        )

        messages.success(self.request, f'Message sent')
        return super().form_valid(form)


class BroadcastMessageActivityLogAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = ActivityLog
    search_values_separator = '+'
    length_menu = [[25, 50, 100, 250, -1], [25, 50, 100, 250, 'all']]
    initial_order = [["created_at", "desc"], ]
    permission_required = ['administration.p_send_broadcast_message']

    def get_initial_queryset(self, request=None):
        qs = self.model.objects.filter(record_slug='broadcast_message')
        return qs

    column_defs = [
        {'name': 'pk', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'created_at', 'visible': True, 'width': '20px', 'searchable': False, },
        {'name': 'author', 'visible': True, 'foreign_field': 'author__details__first_name',
         'searchable': False, 'width': '30px', },
        {'name': 'title', 'title': 'Title', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
        {'name': 'text', 'title': 'Text', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
        {'name': 'sent_to', 'title': 'Sent To', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
        {'name': 'sent_via', 'title': 'Sent Via', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['created_at'] = obj.created_at.strftime("%Y-%m-%d %H:%M")

        author_html = ''
        if obj.author:
            author_html = obj.author.fullname
        elif obj.author_text:
            author_html = obj.author_text
        row['author'] = author_html

        row['title'] = obj.data['title']
        row['text'] = get_datatable_clipped_value(text=obj.data['text'], max_length=150)

        sent_to_map = dict(SendBroadcastMessageForm.SEND_TO_CHOICES)
        row['sent_to'] = sent_to_map[obj.data['sent_to']]

        sent_via_map = dict(SendBroadcastMessageForm.SEND_VIA_CHOICES)
        sent_via = obj.data['sent_via']

        sent_via_list = []
        for method in sent_via:
            value = sent_via_map[method]
            sent_via_list.append(str(value))

        row['sent_via'] = ', '.join(sent_via_list)

        return
