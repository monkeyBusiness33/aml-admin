# Generated by Django 4.0.3 on 2023-06-20 17:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0108_merge_20230608_1617'),
        ('supplier', '0009_alter_fuelagreement_aml_group_company_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fuelagreement',
            name='document',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fuel_agreement_where_source_document', to='organisation.organisationdocument', verbose_name='Document'),
        ),
    ]
