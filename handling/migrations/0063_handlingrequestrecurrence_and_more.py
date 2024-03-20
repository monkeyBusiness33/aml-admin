# Generated by Django 4.0.3 on 2023-02-01 00:16

import core.custom_form_fields
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0062_autoserviceprovisionform_sent_to'),
    ]

    operations = [
        migrations.CreateModel(
            name='HandlingRequestRecurrence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('specific_recurrence_dates', models.CharField(blank=True, max_length=1000, null=True, verbose_name='Specific Dates')),
                ('operating_days', core.custom_form_fields.WeekdayField(blank=True, max_length=14, null=True, verbose_name='Operating Days')),
                ('final_recurrence_date', models.DateTimeField(blank=True, null=True, verbose_name='Final Recurrence Date')),
                ('weeks_of_recurrence', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(54)], verbose_name='Weeks of Recurrence')),
            ],
            options={
                'db_table': 'handling_requests_groups',
            },
        ),
        migrations.CreateModel(
            name='HandlingRequestRecurrenceMission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='handling_requests_membership', to='handling.handlingrequestrecurrence', verbose_name='Group')),
                ('handling_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurrence_groups_membership', to='handling.handlingrequest', verbose_name='Handling Request')),
            ],
            options={
                'db_table': 'handling_requests_groups_missions',
            },
        ),
        migrations.AddField(
            model_name='handlingrequestrecurrence',
            name='handling_requests',
            field=models.ManyToManyField(related_name='recurrence_groups', through='handling.HandlingRequestRecurrenceMission', to='handling.handlingrequest'),
        ),
    ]
