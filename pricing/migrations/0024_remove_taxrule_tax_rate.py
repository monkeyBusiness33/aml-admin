# Generated by Django 4.0.3 on 2022-11-21 16:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0023_remove_taxrule_tax_percentage_alter_taxrule_tax_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxrule',
            name='tax_rate',
        ),
    ]
