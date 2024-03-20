from django.db import models
from django.utils.translation import gettext_lazy as _


class UserSettings(models.Model):
    user = models.OneToOneField("user.User", verbose_name=_("User"),
                                related_name='user_settings',
                                on_delete=models.CASCADE)

    # Chat settings
    chat_enable_sound_notification = models.BooleanField(_("Chat: Enable Sound Notifications"), default=True)

    class Meta:
        db_table = 'users_settings'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from chat.utils.settings import send_updated_user_settings
        try:
            send_updated_user_settings(self.user.person)
        except RuntimeError:
            pass
