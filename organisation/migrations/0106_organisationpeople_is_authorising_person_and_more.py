# Generated by Django 4.0.3 on 2023-05-02 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0105_organisationopsdetails_spf_use_aml_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisationpeople',
            name='is_authorising_person',
            field=models.BooleanField(default=False, verbose_name='Is Authorising Person?'),
        ),
        migrations.AddField(
            model_name='organisationpeoplehistory',
            name='is_authorising_person',
            field=models.BooleanField(default=False, verbose_name='Is Authorising Person?'),
        ),
    ]
