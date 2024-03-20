# Generated by Django 3.2.9 on 2022-03-26 01:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0021_auto_20220326_0101'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ipalocation',
            name='location',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ipas', to='organisation.organisation'),
        ),
        migrations.AlterField(
            model_name='ipalocation',
            name='organisation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisation.organisation'),
        ),
    ]
