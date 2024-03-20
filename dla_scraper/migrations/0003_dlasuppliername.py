# Generated by Django 4.0.3 on 2022-09-06 14:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0091_dlacontractlocation_and_more'),
        ('dla_scraper', '0002_alter_dlacontract_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='DLASupplierName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Supplier Name')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dla_supplier_names', to='organisation.organisation', verbose_name='Supplier')),
            ],
            options={
                'db_table': 'organisations_dla_suppliers_ids',
                'managed': True,
            },
        ),
    ]
