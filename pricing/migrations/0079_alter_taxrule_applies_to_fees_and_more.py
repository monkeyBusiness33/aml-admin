# Generated by Django 4.0.3 on 2023-10-04 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0078_supplierfuelfeerate_specific_hookup_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taxrule',
            name='applies_to_fees',
            field=models.BooleanField(default=False, null=True, verbose_name='Applies to Fees'),
        ),
        migrations.AlterField(
            model_name='taxruleexception',
            name='applies_to_fees',
            field=models.BooleanField(default=False, null=True, verbose_name='Applies to Fees'),
        ),
    ]
