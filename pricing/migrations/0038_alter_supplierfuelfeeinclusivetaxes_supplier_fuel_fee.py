# Generated by Django 4.0.3 on 2023-03-30 10:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0037_alter_fuelpricingmarketplddocument_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplierfuelfeeinclusivetaxes',
            name='supplier_fuel_fee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='fuel_inclusive_taxes', to='pricing.supplierfuelfeerate', verbose_name='Supplier Fuel Fee Rate'),
        ),
    ]
