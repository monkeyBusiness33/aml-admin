# Generated by Django 4.0.3 on 2022-08-11 12:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_flighttype_geographichflighttype'),
        ('pricing', '0002_rename_airport_taxrule_specific_airport_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
            ],
            options={
                'db_table': 'taxes_categories',
            },
        ),
        migrations.RenameField(
            model_name='tax',
            old_name='name',
            new_name='local_name',
        ),
        migrations.AddField(
            model_name='tax',
            name='applicable_country',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='core.country', verbose_name='Applicable Country'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tax',
            name='category',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='pricing.taxcategory', verbose_name='Category'),
            preserve_default=False,
        ),
    ]
