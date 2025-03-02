# Generated by Django 3.2.9 on 2022-03-26 02:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20220326_0101'),
        ('organisation', '0022_auto_20220326_0106'),
    ]

    operations = [
        migrations.CreateModel(
            name='AirportWeightUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'db_table': 'organisations_airports_weight_units',
            },
        ),
        migrations.CreateModel(
            name='AirportDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icao_code', models.CharField(max_length=4, unique=True, verbose_name='ICAO Code')),
                ('iata_code', models.CharField(blank=True, max_length=3, null=True, verbose_name='IATA Code')),
                ('latitude', models.DecimalField(decimal_places=8, max_digits=10, verbose_name='Latitude')),
                ('longitude', models.DecimalField(decimal_places=8, max_digits=11, verbose_name='Longitude')),
                ('maximum_weight', models.IntegerField(verbose_name='Maximum Weight')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active?')),
                ('has_pricing', models.BooleanField(default=False, verbose_name='Has Pricing')),
                ('authority', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='organisation.organisation', verbose_name='Authority')),
                ('currency_override', models.ForeignKey(blank=True, db_column='currency_override', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.currency', verbose_name='Currency Override')),
                ('maximum_weight_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisation.airportweightunit', verbose_name='Maximum Weight Unit')),
                ('organisation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='airport_details', to='organisation.organisation')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='core.region', verbose_name='Region')),
            ],
            options={
                'db_table': 'organisations_airports_details',
            },
        ),
    ]
