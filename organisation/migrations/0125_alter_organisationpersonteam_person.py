# Generated by Django 4.2.6 on 2023-11-29 14:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0033_usersettings'),
        ('organisation', '0124_organisationpersonteam_schedule_managed_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationpersonteam',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='user.person', verbose_name='Person'),
        ),
    ]
