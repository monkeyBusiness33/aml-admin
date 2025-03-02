# Generated by Django 4.0.3 on 2023-03-14 15:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0030_pricingcalculationrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxrule',
            name='applies_to_fees',
            field=models.BooleanField(null=True, verbose_name='Applies to Fees'),
        ),
        migrations.AddField(
            model_name='taxrule',
            name='specific_fee_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pricing.fuelfeecategory', verbose_name='Specific Fee Category'),
        ),
        migrations.AddField(
            model_name='taxruleexception',
            name='applies_to_fees',
            field=models.BooleanField(null=True, verbose_name='Applies to Fees'),
        ),
        migrations.AddField(
            model_name='taxruleexception',
            name='specific_fee_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pricing.fuelfeecategory', verbose_name='Specific Fee Category'),
        ),
    ]
