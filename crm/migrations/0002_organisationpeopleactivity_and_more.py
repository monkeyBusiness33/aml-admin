# Generated by Django 4.0.3 on 2022-04-27 02:19

import app.storage_backends
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0080_alter_organisation_options_and_more'),
        ('user', '0019_alter_persondetails_contact_phone'),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationPeopleActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(verbose_name='Date & Time')),
                ('description', models.CharField(max_length=500, null=True, verbose_name='Description')),
                ('is_pinned', models.BooleanField(default=False, verbose_name='Pinned?')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authored_crm_activities', to='user.person', verbose_name='Recorded By')),
                ('crm_activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.activity', verbose_name='Activity')),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisation.organisation', verbose_name='Organisation')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.person', verbose_name='Person')),
            ],
            options={
                'db_table': 'organisations_people_activities',
            },
        ),
        migrations.CreateModel(
            name='OrganisationPeopleActivityAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=100, verbose_name='Description')),
                ('file', models.FileField(storage=app.storage_backends.OrganisationPeopleActivityStorage(), upload_to='', verbose_name='Attachment')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.organisationpeopleactivity', verbose_name='Activity')),
            ],
            options={
                'db_table': 'organisations_people_activities_attachments',
            },
        ),
    ]
