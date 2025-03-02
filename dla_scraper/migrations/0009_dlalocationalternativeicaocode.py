# Generated by Django 4.0.3 on 2022-09-16 12:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0092_dlacontractlocation_ipa'),
        ('dla_scraper', '0008_alter_dlascraperrun_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='DLALocationAlternativeIcaoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icao_code', models.CharField(max_length=4, verbose_name='ICAO Code')),
                ('location', models.ForeignKey(limit_choices_to={'details__type_id': 8}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dla_location_alternative_icao_codes', to='organisation.organisation', verbose_name='Location')),
            ],
            options={
                'db_table': 'organisations_dla_alternative_icao_codes',
                'ordering': ['location__airport_details__icao_code'],
                'permissions': [('reconcile_dla_icao_code', 'Can reconcile alternative ICAO codes for DLA scraper')],
                'managed': True,
            },
        ),
    ]
