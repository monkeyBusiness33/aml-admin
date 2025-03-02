# Generated by Django 4.0.3 on 2023-10-16 11:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0109_alter_operatorpreferredgroundhandler_ground_handler_and_more'),
        ('pricing', '0084_taxrule_specific_fuel_cat_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplierfuelfee',
            name='ipa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fuel_fees_where_is_ipa', to='organisation.organisation', verbose_name='IPA'),
        ),
    ]
