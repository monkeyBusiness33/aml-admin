# Generated by Django 4.2.6 on 2023-11-27 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0109_handlingrequestamendmentsession_aircraft_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequestamendmentsession',
            name='is_departure_update_after_arrival',
            field=models.BooleanField(default=False, verbose_name='Is Departure Change After Arrival?'),
        ),
    ]
