# Generated by Django 4.0.3 on 2022-11-10 10:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0002_rename_supplierfuelagreement_fuelagreement'),
        ('core', '0030_rename_specific_fuel_id_unitofmeasurementconversionmethod_specific_fuel'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='supplier_fuel_agreement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='supplier.fuelagreement'),
        ),
    ]
