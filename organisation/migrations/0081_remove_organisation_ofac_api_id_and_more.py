# Generated by Django 4.0.3 on 2022-04-28 23:38

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0080_alter_organisation_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organisation',
            name='ofac_api_id',
        ),
        migrations.AddField(
            model_name='organisation',
            name='is_sanctioned_ofac',
            field=models.BooleanField(default=False, verbose_name='Is Sanctioned OFAC?'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='ofac_latest_update',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
