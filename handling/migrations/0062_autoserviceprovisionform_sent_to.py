# Generated by Django 4.0.3 on 2023-01-27 12:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0103_organisationopsdetails'),
        ('handling', '0061_handlingrequestamendmentsession_is_gh_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='autoserviceprovisionform',
            name='sent_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_spf_submissions', to='organisation.organisation', verbose_name='Ground Handler'),
        ),
    ]
