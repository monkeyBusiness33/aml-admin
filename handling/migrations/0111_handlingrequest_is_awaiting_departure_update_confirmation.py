# Generated by Django 4.2.6 on 2023-11-27 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0110_handlingrequestamendmentsession_is_departure_update_after_arrival'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequest',
            name='is_awaiting_departure_update_confirmation',
            field=models.BooleanField(default=False, verbose_name='Is Awaiting Departure Update Confirmation?'),
        ),
    ]
