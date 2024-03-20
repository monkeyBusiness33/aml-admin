from core.models.settings import GlobalConfiguration


class Permissions(GlobalConfiguration):

    class Meta:
        proxy = True

        permissions = [
            ('p_view', 'Administration section pages view'),
            ('p_staff_user_invite', 'Staff User: Invite'),
            ('p_staff_user_edit', 'Staff User: Edit'),
            ('p_staff_user_suspend', 'Staff User: Suspend/Activate'),
            ('p_staff_user_reset_qr', 'Staff User: Reset TOTP (QR Code)'),
            ('p_staff_user_delete', 'Staff User: Delete'),

            ('p_staff_role_create', 'Staff Role: Create'),
            ('p_staff_role_edit', 'Staff Role: Edit'),

            ('p_dla_contract_scrapper', 'DLA Contract Scrapper (All Actions)'),
            ('p_send_broadcast_message', 'Send Broadcast Message'),
            ('p_email_distribution_control', 'Email Distribution Control'),
        ]
