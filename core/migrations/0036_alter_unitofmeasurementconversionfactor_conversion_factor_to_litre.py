# Generated by Django 4.0.3 on 2023-03-07 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_rename_usg_conversion_factor_unitofmeasurementconversionfactor_conversion_factor_to_litre_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='unitofmeasurementconversionfactor',
            name='conversion_factor_to_litre',
            field=models.DecimalField(decimal_places=4, max_digits=12, verbose_name='Conversion Factor to Litre'),
        ),
    ]
