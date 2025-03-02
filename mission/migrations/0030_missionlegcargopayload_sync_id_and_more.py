# Generated by Django 4.0.3 on 2023-09-25 14:29

from django.db import migrations
import shortuuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('mission', '0029_alter_missionturnaroundservice_updated_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionlegcargopayload',
            name='sync_id',
            field=shortuuidfield.fields.ShortUUIDField(blank=True, editable=False, max_length=22),
        ),
        migrations.AddField(
            model_name='missionlegpassengerspayload',
            name='sync_id',
            field=shortuuidfield.fields.ShortUUIDField(blank=True, editable=False, max_length=22),
        ),
    ]
