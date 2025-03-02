# Generated by Django 4.0.3 on 2022-11-15 11:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0098_ipalocation_location_email_and_more'),
        ('pricing', '0017_fuelagreementpricingmanual_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelindex',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Is Active?'),
        ),
        migrations.AddField(
            model_name='fuelindex',
            name='provider',
            field=models.ForeignKey(default=100007, on_delete=django.db.models.deletion.CASCADE, to='organisation.organisation', verbose_name='Provider'),
            preserve_default=False,
        ),
    ]
