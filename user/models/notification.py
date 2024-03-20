from notifications.base.models import AbstractNotification


class CustomNotification(AbstractNotification):

    class Meta(AbstractNotification.Meta):
        abstract = False
        db_table = 'users_notifications'
        app_label = 'user'
