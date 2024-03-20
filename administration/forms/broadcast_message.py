from django import forms
from django.forms import widgets
from django.utils.translation import gettext_lazy as _


class SendBroadcastMessageForm(forms.Form):

    title = forms.CharField(
        widget=widgets.TextInput(attrs={
                'class': 'form-control',
            }),
    )
    text = forms.CharField(
        widget=widgets.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'maxlength': 500,
        }),
    )

    SEND_VIA_CHOICES = (
        ('push', _("Push Notification")),
        ('web', _("Web App")),
    )
    send_via = forms.MultipleChoiceField(
        choices=SEND_VIA_CHOICES,
        label='Send via',
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
    )

    SEND_TO_CHOICES = (
        ('all_users', _("All Users")),
        ('staff', _("Only Staff")),
        ('clients', _("Only DLA users (mobile app and planner portal)")),
    )
    send_to = forms.ChoiceField(
        choices=SEND_TO_CHOICES,
        label='Send To',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
    )
