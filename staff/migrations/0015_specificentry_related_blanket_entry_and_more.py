# Generated by Django 4.2.6 on 2023-12-12 14:05

import django.contrib.postgres.fields
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0014_rename_role_teamrole_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='specificentry',
            name='related_blanket_entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='staff.blanketentry', verbose_name='Replaces Entry'),
        ),
        migrations.AlterField(
            model_name='blanketentry',
            name='applied_on_weeks',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(53)], verbose_name='Applied on Weeks'), size=None),
        ),
        migrations.AlterField(
            model_name='blanketentryoverride',
            name='applied_on_weeks',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(53)], verbose_name='Applied on Weeks'), size=None),
        ),
    ]
