# Generated by Django 4.0.3 on 2023-08-17 14:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0065_remove_fuelindex_index_period_is_daily_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fuelagreementpricingformula',
            name='pricing_index',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='pricing.fuelindexdetails', verbose_name='Pricing Index'),
        ),
    ]
