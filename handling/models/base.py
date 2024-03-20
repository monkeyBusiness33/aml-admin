from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models.settings import GlobalConfiguration


class Permissions(GlobalConfiguration):
    class Meta:
        proxy = True

        permissions = [
            ('p_view', 'DoD Servicing: View section pages'),
            ('p_dod_comms', 'DoD Servicing: DoD Comms chat access'),
            ('p_sfr_export_data', 'DoD Servicing: S&F Request Data Export'),
            ('p_create', 'DoD Servicing: Create anything'),
            ('p_update', 'DoD Servicing: Update anything'),
            ('p_activity_log_view', 'DoD Servicing: View Activity Log'),
            ('p_dla_services_update', 'DoD Servicing: Create or Update DLA Services'),
            ('p_dla_services_view', 'DoD Servicing: View DLA Services'),
            ('p_spf_v2_reconcile', 'DoD Servicing: Reconcile SPF'),
            ('p_manage_sfr_ops_checklist_settings', 'DoD Servicing: Manage SFR Ops Checklist Settings'),
            ('p_admin_edit', 'DoD Servicing: "Admin Edit Functionality"'),
            ('p_request_signed_spf', 'DoD Servicing: "Send Signed SPF Request"'),
            ('p_create_retrospective_sfr', 'DoD Servicing: "Create retrospective SPF Request"'),
        ]


class HandlingRequestType(models.Model):
    name = models.CharField(_("Name"), max_length=50)

    class Meta:
        db_table = 'handling_requests_types'
        app_label = 'handling'

    def __str__(self):
        return f'{self.name}'


class HandlingRequestFeedback(models.Model):
    handling_request = models.ForeignKey("handling.HandlingRequest",
                                         verbose_name=_("Handling Request"),
                                         related_name='feedback',
                                         on_delete=models.CASCADE)
    fuelling_feedback = models.CharField(_("Fueling Feedback"),
                                         max_length=500, null=True)
    servicing_feedback = models.CharField(_("Ground Servicing Feedback"),
                                          max_length=500, null=True)
    created_at = models.DateTimeField(_("Date"), auto_now=False, auto_now_add=True)

    class Meta:
        db_table = 'handling_requests_feedback'
        app_label = 'handling'


class HandlingRequestNotificationsLog(models.Model):
    handling_request = models.OneToOneField("handling.HandlingRequest",
                                            related_name='notifications',
                                            on_delete=models.CASCADE)
    is_handler_parking_confirmation_email_sent = models.BooleanField(_("Handler Parking Confirmation Email Sent"),
                                                                     default=False)
    is_spf_gh_request_email_sent = models.BooleanField(_("GH SPF Request Sent"), default=False)

    class Meta:
        db_table = 'handling_requests_notifications_log'
        app_label = 'handling'
