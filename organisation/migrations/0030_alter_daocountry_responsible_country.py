# Generated by Django 3.2.9 on 2022-03-27 02:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20220326_0101'),
        ('organisation', '0029_alter_organisation_dao_countries'),
    ]

    operations = [
        migrations.AlterField(
            model_name='daocountry',
            name='responsible_country',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='country_dao', to='core.country', verbose_name='Country'),
        ),
    ]
