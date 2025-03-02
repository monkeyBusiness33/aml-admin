# Generated by Django 4.0.3 on 2023-03-01 17:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_pricingunit_description_short'),
        ('organisation', '0103_organisationopsdetails'),
    ]

    operations = [
        migrations.AddField(
            model_name='operatordetails',
            name='crew_weight',
            field=models.IntegerField(blank=True, null=True, verbose_name='Crew Weight'),
        ),
        migrations.AddField(
            model_name='operatordetails',
            name='pax_crew_weight_uom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operators_pax_crew_weight', to='core.unitofmeasurement', verbose_name='Pax & Crew Weight Unit'),
        ),
        migrations.AddField(
            model_name='operatordetails',
            name='pax_weight_female',
            field=models.IntegerField(blank=True, null=True, verbose_name='Pax Weight Female'),
        ),
        migrations.AddField(
            model_name='operatordetails',
            name='pax_weight_male',
            field=models.IntegerField(blank=True, null=True, verbose_name='Pax Weight Male'),
        ),
    ]
