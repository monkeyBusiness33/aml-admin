# Generated by Django 4.2.6 on 2023-11-07 15:54

from django.db import migrations
import shortuuidfield.fields


class Migration(migrations.Migration):
    dependencies = [
        ("mission", "0033_create_mission_status_flags"),
    ]

    operations = [
        migrations.AlterField(
            model_name="missionlegcargopayload",
            name="sync_id",
            field=shortuuidfield.fields.ShortUUIDField(
                blank=True, editable=False, max_length=22
            ),
        ),
        migrations.AlterField(
            model_name="missionlegpassengerspayload",
            name="sync_id",
            field=shortuuidfield.fields.ShortUUIDField(
                blank=True, editable=False, max_length=22
            ),
        ),
    ]
