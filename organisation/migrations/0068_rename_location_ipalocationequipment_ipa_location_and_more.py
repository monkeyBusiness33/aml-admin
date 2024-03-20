# Generated by Django 4.0.3 on 2022-04-20 00:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_comment'),
        ('organisation', '0067_rename_location_ipalocationfuel_ipa_location'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ipalocationequipment',
            old_name='location',
            new_name='ipa_location',
        ),
        migrations.AddField(
            model_name='ipalocation',
            name='fuel',
            field=models.ManyToManyField(blank=True, related_name='ipa_locations', through='organisation.IpaLocationFuel', to='core.fueltype'),
        ),
        migrations.AlterField(
            model_name='ipalocationfuel',
            name='fuel_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_locations_fuel', to='core.fueltype', verbose_name='Fuel Type'),
        ),
    ]
