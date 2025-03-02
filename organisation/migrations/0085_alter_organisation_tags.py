# Generated by Django 4.0.3 on 2022-05-17 00:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_tag_is_system'),
        ('organisation', '0084_alter_oilcodetails_iata_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='tags',
            field=models.ManyToManyField(blank=True, limit_choices_to={'is_system': False}, related_name='organisations', through='organisation.OrganisationTag', to='core.tag'),
        ),
    ]
