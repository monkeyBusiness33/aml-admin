# Generated by Django 3.2.9 on 2022-03-27 00:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aircraft', '0006_remove_aircrafthistory_homebase'),
    ]

    operations = [
        migrations.RenameField(
            model_name='aircrafthistory',
            old_name='homebase_fk',
            new_name='homebase',
        ),
    ]
