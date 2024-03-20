# Generated by Django 4.2.6 on 2023-11-22 23:16

from django.db import migrations


def migrate_data(apps, schema):
    cargo_payload_cls = apps.get_model('mission', 'MissionLegCargoPayload')
    cargo_payloads = cargo_payload_cls.objects.all()

    for cargo_payload in cargo_payloads:
        cargo_payload.mission_legs.add(cargo_payload.mission_leg)


class Migration(migrations.Migration):
    dependencies = [
        ("mission", "0038_missioncargomissionleg_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_data)
    ]
