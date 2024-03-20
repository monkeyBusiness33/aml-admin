from .settings import GlobalConfiguration


class Permissions(GlobalConfiguration):

    class Meta:
        proxy = True

        permissions = [
            # Contacts Section permissions
            ('p_contacts_view', 'Contacts: All pages view'),
            ('p_contacts_create', 'Contacts: Create any item'),
            ('p_contacts_update', 'Contacts: Update anything'),
            ('p_contacts_moderate', 'Contacts: Review Created Organisation / Person / Aircraft'),
            ('p_contacts_sanctioned_ignore', 'Contacts: Ignore sanctioned'),
            ('p_contacts_sanctioned_delete', 'Contacts: Sanction Exceptions Delete'),
            ('p_contacts_person_app_access_add', 'Contacts: Update person "Application Access" field'),
            ('p_contacts_person_app_access_del', 'Contacts: Revoke person external access'),
            ('p_contacts_person_password_reset', 'Contacts: Send person password reset email message'),

            # Additional Contact Details section in Organisation Details tab
            ('p_contacts_additional_contact_details_view', 'Contacts: View Additional Contact Details'),
            ('p_contacts_additional_contact_details_create', 'Contacts: Create Additional Contact Details'),
            ('p_contacts_additional_contact_details_update', 'Contacts: Update Additional Contact Details'),
            ('p_contacts_additional_contact_details_delete', 'Contacts: Delete Additional Contact Details'),

            # Comments
            ('p_comments_create', 'Comments: Create comment'),
            ('p_comments_moderate', 'Comments: Moderate comments (delete other users comments)'),

            # Activity Log
            ('p_activity_log_view', 'Global: View Activity Log'),
        ]
