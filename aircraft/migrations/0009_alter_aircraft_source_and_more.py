# Generated by Django 4.0.3 on 2022-04-09 01:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aircraft', '0008_alter_aircrafthistory_homebase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aircraft',
            name='source',
            field=models.CharField(default='AML', max_length=6, verbose_name='Source'),
        ),
        migrations.AlterField(
            model_name='aircrafthistory',
            name='change_effective_date',
            field=models.DateField(auto_now_add=True, verbose_name='Change Date'),
        ),
        migrations.AlterField(
            model_name='aircrafthistory',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='aircrafthistory',
            name='source',
            field=models.CharField(default='AML', max_length=6, verbose_name='Source'),
        ),
    ]
