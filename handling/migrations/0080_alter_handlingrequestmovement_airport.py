# Generated by Django 4.0.3 on 2023-05-09 14:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0106_organisationpeople_is_authorising_person_and_more'),
        ('handling', '0079_handlingrequestdocumentfile_signed_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='handlingrequestmovement',
            name='airport',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisation.organisation', verbose_name='Airport'),
        ),
    ]
