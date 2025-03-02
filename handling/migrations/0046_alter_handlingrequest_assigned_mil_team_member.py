# Generated by Django 4.0.3 on 2022-10-18 00:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0024_user_last_token_sent_at'),
        ('handling', '0045_handlingrequest_assigned_mil_team_member'),
    ]

    operations = [
        migrations.AlterField(
            model_name='handlingrequest',
            name='assigned_mil_team_member',
            field=models.ForeignKey(blank=True, limit_choices_to={'user__roles': 1000}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assigned_handling_requests', to='user.person', verbose_name='Assigned Mil Team Member'),
        ),
    ]
