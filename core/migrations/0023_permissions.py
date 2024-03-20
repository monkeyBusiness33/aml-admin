# Generated by Django 4.0.3 on 2022-10-23 20:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_globalconfiguration'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permissions',
            fields=[
            ],
            options={
                'permissions': [('ops_handling_update_callsign', 'Update S&F Request Callsign'), ('ops_handling_update_mission_number', 'Update S&F Request Mission Number'), ('ops_handling_update_mission_type', 'Update S&F Request Mission Type')],
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.globalconfiguration',),
        ),
    ]
