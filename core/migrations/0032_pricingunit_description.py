# Generated by Django 4.0.3 on 2022-11-11 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_comment_supplier_fuel_agreement'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricingunit',
            name='description',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Description'),
        ),
    ]
