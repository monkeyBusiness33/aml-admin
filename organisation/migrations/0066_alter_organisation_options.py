# Generated by Django 4.0.3 on 2022-04-19 23:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0065_alter_handlerdetails_contact_phone_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='organisation',
            options={'ordering': ['details__registered_name'], 'permissions': [('add_aircraft_operator', 'Add Aircraft Operator'), ('view_aircraft_operator', 'View Aircraft Operator Organisation'), ('view_airport', 'View Airport Organisation'), ('view_dao', 'View DAO (Defense Attache Offices)'), ('view_fuel_agent', 'View Fuel Agent'), ('change_fuel_agent', 'Edit (change) Fuel Agent'), ('view_fuel_reseller', 'View Fuel Reseller'), ('change_fuel_reseller', 'Edit (change) Fuel Reseller'), ('change_ipa', 'Edit (change) Into-Plane Agent (IPA)')]},
        ),
    ]
