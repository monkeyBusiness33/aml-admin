# Generated by Django 4.0.3 on 2022-11-21 17:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_pricingunit_description_short'),
        ('pricing', '0024_remove_taxrule_tax_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='tax',
            name='applicable_region',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.region', verbose_name='Applicable Region'),
        ),
        migrations.AlterField(
            model_name='tax',
            name='applicable_country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.country', verbose_name='Applicable Country'),
        ),
    ]
