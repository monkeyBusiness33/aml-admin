# Generated by Django 4.0.3 on 2023-03-04 00:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0103_organisationopsdetails'),
        ('pricing', '0029_alter_fuelindexpricing_fuel_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fuelpricingmarketpld',
            name='source_document_url',
            field=models.ForeignKey(blank=True, db_column='source_document_url', null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisation.organisationdocument', verbose_name='Source Document'),
        ),
        migrations.RemoveField(
            model_name='fuelpricingmarketpldlocation',
            name='location',
        ),
        migrations.AddField(
            model_name='fuelpricingmarketpldlocation',
            name='location',
            field=models.ManyToManyField(limit_choices_to={'airport_details__isnull': False, 'details__type_id': 8}, related_name='fuel_pricing_market_plds_at_location', to='organisation.organisation', verbose_name='Location'),
        ),
    ]
