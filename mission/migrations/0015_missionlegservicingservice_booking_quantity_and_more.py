# Generated by Django 4.0.3 on 2023-07-11 12:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_activitylog_mission_leg'),
        ('mission', '0014_alter_missioncrewposition_legs'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionlegservicingservice',
            name='booking_quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Quantity Required'),
        ),
        migrations.AddField(
            model_name='missionlegservicingservice',
            name='booking_quantity_uom',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_fluid_uom': True}, null=True, on_delete=django.db.models.deletion.RESTRICT, to='core.unitofmeasurement', verbose_name='Quantity Required UOM'),
        ),
        migrations.AddField(
            model_name='missionlegservicingservice',
            name='booking_text',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Details'),
        ),
    ]
