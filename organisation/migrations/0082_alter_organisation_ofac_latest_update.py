# Generated by Django 4.0.3 on 2022-04-29 02:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0081_remove_organisation_ofac_api_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='ofac_latest_update',
            field=models.DateTimeField(null=True),
        ),
    ]
