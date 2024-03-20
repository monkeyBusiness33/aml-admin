# Generated by Django 4.0.3 on 2023-08-03 17:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_alter_permissions_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='permissions',
            options={'permissions': [('p_contacts_view', 'Contacts: All pages view'), ('p_contacts_create', 'Contacts: Create any item'), ('p_contacts_update', 'Contacts: Update anything'), ('p_contacts_moderate', 'Contacts: Review Created Organisation / Person / Aircraft'), ('p_contacts_sanctioned_ignore', 'Contacts: Ignore sanctioned'), ('p_contacts_sanctioned_delete', 'Contacts: Sanction Exceptions Delete'), ('p_contacts_person_app_access_add', 'Contacts: Update person "Application Access" field'), ('p_contacts_person_app_access_del', 'Contacts: Revoke person external access'), ('p_contacts_person_password_reset', 'Contacts: Send person password reset email message'), ('p_comments_create', 'Comments: Create comment'), ('p_comments_moderate', 'Comments: Moderate comments (delete other users comments)')]},
        ),
    ]
