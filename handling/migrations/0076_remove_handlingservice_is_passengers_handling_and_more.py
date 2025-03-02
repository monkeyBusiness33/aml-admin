# Generated by Django 4.0.3 on 2023-03-07 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0075_handlingservicespfrepresentation_represent_as_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='handlingservice',
            name='is_passengers_handling',
        ),
        migrations.AlterField(
            model_name='handlingservice',
            name='represent_in_spf_as',
            field=models.ManyToManyField(blank=True, related_name='spf_represented_by', through='handling.HandlingServiceSpfRepresentation', to='handling.handlingservice', verbose_name='Represent in SPF as'),
        ),
    ]
