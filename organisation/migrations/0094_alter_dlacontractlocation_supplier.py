# Generated by Django 4.0.3 on 2022-09-20 11:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0093_organisationaircrafttype_mtow_override_kg_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dlacontractlocation',
            name='supplier',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dla_contracted_locations_rev', to='organisation.organisation'),
        ),
    ]
