# Generated by Django 4.0.3 on 2023-03-03 01:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0070_handlingrequestcargopayload'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='handlingrequestpassengerspayload',
            table='handling_requests_payloads_passengers',
        ),
    ]
