# Generated by Django 4.0.3 on 2022-05-16 00:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aircraft', '0012_alter_aircraft_type'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='aircrafttype',
            options={'ordering': ['manufacturer']},
        ),
    ]
