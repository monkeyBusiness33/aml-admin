# Generated by Django 4.0.3 on 2022-08-01 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0036_handlingrequest_apacs_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequest',
            name='fuel_prist_required',
            field=models.BooleanField(default=False, verbose_name='Prist Required'),
        ),
    ]
