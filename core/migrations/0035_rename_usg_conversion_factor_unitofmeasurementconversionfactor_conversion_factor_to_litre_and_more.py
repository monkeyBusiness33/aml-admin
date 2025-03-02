# Generated by Django 4.0.3 on 2023-03-07 13:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0024_user_last_token_sent_at'),
        ('core', '0034_alter_pricingunit_options'),
    ]

    operations = [
        migrations.RenameField(
            model_name='unitofmeasurementconversionfactor',
            old_name='usg_conversion_factor',
            new_name='conversion_factor_to_litre',
        ),
        migrations.AddField(
            model_name='unitofmeasurementconversionfactor',
            name='specific_fuel',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='uom_conversions_ratio_to_l_for_this_fuel', to='core.fueltype', verbose_name='Specific Fuel'),
        ),
        migrations.AddField(
            model_name='unitofmeasurementconversionfactor',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Updated At'),
        ),
        migrations.AddField(
            model_name='unitofmeasurementconversionfactor',
            name='updated_by',
            field=models.ForeignKey(db_column='updated_by', default=7, on_delete=django.db.models.deletion.RESTRICT, to='user.person', verbose_name='Updated By'),
        ),
    ]
