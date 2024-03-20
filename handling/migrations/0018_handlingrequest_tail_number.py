# Generated by Django 4.0.3 on 2022-05-05 01:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('aircraft', '0011_alter_aircrafthistory_homebase'),
        ('handling', '0017_remove_handlingrequest_tail_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequest',
            name='tail_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='aircraft.aircrafthistory', verbose_name='Tail Number'),
        ),
    ]
