# Generated by Django 4.0.3 on 2022-05-03 01:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0083_alter_organisation_options'),
        ('handling', '0013_alter_handlingrequest_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='handlingrequest',
            name='handling_agent',
            field=models.ForeignKey(blank=True, limit_choices_to={'details__type_id': 3, 'handler_details__isnull': False}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handler_handling_requests', to='organisation.organisation', verbose_name='Handling Agent'),
        ),
    ]
