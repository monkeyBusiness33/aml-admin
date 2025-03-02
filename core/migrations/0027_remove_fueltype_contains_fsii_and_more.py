# Generated by Django 4.0.3 on 2022-11-01 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_fueladditive_fueltypeblend_fueltypeblendcomponent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fueltype',
            name='contains_fsii',
        ),
        migrations.RemoveField(
            model_name='fueltype',
            name='contains_prist',
        ),
        migrations.RemoveField(
            model_name='fueltype',
            name='nato_code',
        ),
        migrations.AddField(
            model_name='fueltype',
            name='is_blend',
            field=models.BooleanField(default=False, verbose_name='Is Blend?'),
        ),
    ]
