# Generated by Django 4.0.3 on 2023-06-02 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mission', '0005_mission_air_card_prefix_missionleg_air_card_prefix'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='air_card_expiration',
            field=models.CharField(blank=True, max_length=5, null=True, verbose_name='AIR Card Expiration'),
        ),
        migrations.AlterField(
            model_name='missionleg',
            name='air_card_expiration',
            field=models.CharField(blank=True, max_length=5, null=True, verbose_name='AIR Card Expiration'),
        ),
    ]
