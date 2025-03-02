# Generated by Django 4.2.7 on 2023-12-04 11:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0127_remove_organisationpersonteam_manages_team_schedule_and_more'),
        ('staff', '0005_alter_blanketentry_updated_on_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blanketentry',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_blanket_entries', to='organisation.organisationamlteam', verbose_name='Team'),
        ),
        migrations.AlterField(
            model_name='blanketentryoverride',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_blanket_entry_overrides', to='organisation.organisationamlteam', verbose_name='Team'),
        ),
        migrations.AlterField(
            model_name='specificentry',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_specific_entries', to='organisation.organisationamlteam', verbose_name='Team'),
        ),
    ]
