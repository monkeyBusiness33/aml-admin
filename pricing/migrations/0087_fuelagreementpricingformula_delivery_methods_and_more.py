# Generated by Django 4.0.3 on 2023-10-16 16:01

from django.db import migrations, models


def convert_existing_delivery_methods(apps, schema_editor):
    market_pricing_cls = apps.get_model('pricing', 'FuelPricingMarket')
    discount_pricing_cls = apps.get_model('pricing', 'FuelAgreementPricingManual')
    formula_pricing_cls = apps.get_model('pricing', 'FuelAgreementPricingFormula')

    for cls in [market_pricing_cls, discount_pricing_cls, formula_pricing_cls]:
        for pricing in cls.objects.all():
            if pricing.delivery_method:
                pricing.delivery_methods.add(pricing.delivery_method)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_hookupmethod'),
        ('pricing', '0086_fuelpricingmarketdeliverymethod_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelagreementpricingformula',
            name='delivery_methods',
            field=models.ManyToManyField(related_name='fuel_agreement_pricing_formula', through='pricing.FuelAgreementPricingFormulaDeliveryMethods', to='core.fuelequipmenttype', verbose_name='Delivery Method(s)'),
        ),
        migrations.AddField(
            model_name='fuelagreementpricingmanual',
            name='delivery_methods',
            field=models.ManyToManyField(related_name='fuel_agreement_pricing_discount', through='pricing.FuelAgreementPricingManualDeliveryMethods', to='core.fuelequipmenttype', verbose_name='Delivery Method(s)'),
        ),
        migrations.AddField(
            model_name='fuelpricingmarket',
            name='delivery_methods',
            field=models.ManyToManyField(related_name='fuel_market_pricing', through='pricing.FuelPricingMarketDeliveryMethod', to='core.fuelequipmenttype', verbose_name='Delivery Method(s)'),
        ),
        migrations.RunPython(convert_existing_delivery_methods, reverse_code=migrations.RunPython.noop),
    ]
