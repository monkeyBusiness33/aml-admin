# Generated by Django 4.0.3 on 2022-05-03 01:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0014_alter_handlingrequest_handling_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequest',
            name='dla_contracted_fuel',
            field=models.BooleanField(default=False, verbose_name='DLA Contracted Location'),
        ),
    ]
