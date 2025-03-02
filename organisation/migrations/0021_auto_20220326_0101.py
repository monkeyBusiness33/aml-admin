# Generated by Django 3.2.9 on 2022-03-26 01:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20220326_0101'),
        ('organisation', '0020_alter_organisation_ofac_api_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='IpaLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_locations2', to='organisation.organisation')),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_locations1', to='organisation.organisation')),
            ],
            options={
                'db_table': 'organisations_ipa_locations',
            },
        ),
        migrations.CreateModel(
            name='IpaLocationEquipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('fuel_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_location_equipment', to='core.fueltype', verbose_name='Fuel Type')),
                ('fuel_uom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_location_equipment', to='core.unitofmeasurement', verbose_name='UOM')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment', to='organisation.ipalocation')),
                ('temperature_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.temperatureunit', verbose_name='Temperature Unit')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_location_equipment', to='core.fuelequipmenttype', verbose_name='Type')),
            ],
            options={
                'db_table': 'organisations_ipa_locations_equipment',
            },
        ),
        migrations.CreateModel(
            name='IpaDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iata_code', models.CharField(max_length=10, null=True, verbose_name='IATA Code')),
                ('organisation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ipa_details', to='organisation.organisation')),
            ],
            options={
                'db_table': 'organisations_ipa_details',
            },
        ),
        migrations.AddField(
            model_name='organisation',
            name='ipa_locations',
            field=models.ManyToManyField(through='organisation.IpaLocation', to='organisation.Organisation'),
        ),
    ]
