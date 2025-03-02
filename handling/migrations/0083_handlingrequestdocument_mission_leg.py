# Generated by Django 4.0.3 on 2023-05-31 17:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mission', '0004_missionlegservicing_handling_request'),
        ('handling', '0082_handlingrequestdocument_mission_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequestdocument',
            name='mission_leg',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='mission.missionleg', verbose_name='Mission Leg'),
        ),
    ]
