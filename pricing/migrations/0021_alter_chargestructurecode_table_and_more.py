# Generated by Django 4.0.3 on 2022-11-17 14:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0020_alter_chargestructurecode_table_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='chargestructurecode',
            table='charge_structure_codes',
        ),
        migrations.AlterModelTable(
            name='chargestructurequalifier',
            table='charge_structure_qualifiers',
        ),
    ]
