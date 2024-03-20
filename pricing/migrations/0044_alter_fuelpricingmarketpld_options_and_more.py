# Generated by Django 4.0.3 on 2023-06-01 06:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0107_merge_20230505_1344'),
        ('aircraft', '0021_merge_20230505_1344'),
        ('core', '0038_merge_20230505_1344'),
        ('pricing', '0043_merge_20230523_1433'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fuelpricingmarketpld',
            options={'permissions': [('can_supersede_pld', "Can supersede the Price List Document to change the 'current' status"), ('can_alter_pricing_publication_status', 'Can alter PLD attached pricing publication status')]},
        ),
        migrations.AlterModelOptions(
            name='fuelpricingmarketplddocument',
            options={},
        ),
        migrations.AlterField(
            model_name='fuelpricingmarket',
            name='ipa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='fuel_pricing_markets_where_is_ipa', to='organisation.organisation', verbose_name='IPA'),
        ),
        migrations.AlterField(
            model_name='supplierfuelfeerate',
            name='delivery_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.fuelequipmenttype', verbose_name='Delivery Method'),
        ),
        migrations.AlterField(
            model_name='supplierfuelfeerate',
            name='quantity_band_uom',
            field=models.ForeignKey(blank=True, db_column='quantity_band_uom', null=True, on_delete=django.db.models.deletion.RESTRICT, to='core.unitofmeasurement', verbose_name='Quantity Band Unit'),
        ),
        migrations.AlterField(
            model_name='supplierfuelfeerate',
            name='specific_fuel',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.fueltype', verbose_name='Specific Fuel'),
        ),
        migrations.AlterField(
            model_name='supplierfuelfeerate',
            name='weight_band',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='aircraft.aircraftweightunit', verbose_name='Weight Band Unit'),
        ),
        migrations.AlterField(
            model_name='taxrule',
            name='tax_rate_percentage',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tax_rules', to='pricing.taxratepercentage', verbose_name='Tax Rate Percentage'),
        ),
    ]
