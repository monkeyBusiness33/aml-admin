# Generated by Django 4.2.6 on 2023-12-13 12:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mission", "0041_mission_mission_number_prefix_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="missionleg",
            name="arrival_datetime",
            field=models.DateTimeField(verbose_name="Arrival Date & Time (Z)"),
        ),
        migrations.AlterField(
            model_name="missionleg",
            name="departure_datetime",
            field=models.DateTimeField(verbose_name="Departure Date & Time (Z)"),
        ),
    ]
