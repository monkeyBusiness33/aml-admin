# Generated by Django 4.0.3 on 2023-02-03 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0065_alter_handlingrequestrecurrencemission_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequestfuelbooking',
            name='is_confirmed',
            field=models.BooleanField(default=True, verbose_name='Fuel Booking Confirmed'),
        ),
    ]
