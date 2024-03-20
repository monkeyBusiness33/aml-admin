# Generated by Django 4.2.6 on 2023-11-22 14:27

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("handling", "0108_alter_handlingrequestopschecklistitem_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="handlingservice",
            name="is_spf_v2_non_dla",
            field=models.BooleanField(
                default=False, verbose_name="SPFv2: Optional Service (Overrides is_dla)"
            ),
        ),
    ]
