# Generated by Django 4.0.3 on 2023-07-17 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mission', '0015_missionlegservicingservice_booking_quantity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionlegservicingservice',
            name='note',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Note'),
        ),
    ]
