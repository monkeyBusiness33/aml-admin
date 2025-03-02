# Generated by Django 4.0.3 on 2022-05-06 00:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('aircraft', '0011_alter_aircrafthistory_homebase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aircraft',
            name='type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aircraft_list', to='aircraft.aircrafttype', verbose_name='Aircraft Type'),
        ),
    ]
