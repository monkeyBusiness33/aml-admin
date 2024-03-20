# Generated by Django 4.0.3 on 2022-08-05 00:14

from django.db import migrations


def move_contact_person_to_crew(apps, schema_editor):
    HandlingRequest = apps.get_model('handling', 'HandlingRequest')
    HandlingRequestCrew = apps.get_model('handling', 'HandlingRequestCrew')

    for handling_request in HandlingRequest.objects.all():
        if handling_request.customer_person:
            obj, created = HandlingRequestCrew.objects.update_or_create(
                handling_request=handling_request, person=handling_request.customer_person,
                defaults={
                    'position_id': 1,
                    'is_primary_contact': True,
                    'can_update_mission': True,
                }
            )


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0038_handlingrequestcrew_and_more'),
    ]

    operations = [
        migrations.RunPython(move_contact_person_to_crew)
    ]
