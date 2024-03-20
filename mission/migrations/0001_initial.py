# Generated by Django 4.0.3 on 2023-05-17 16:45

import app.storage_backends
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('aircraft', '0018_aircraftdesignator_aircrafttype_type_designator'),
        ('handling', '0080_alter_handlingrequestmovement_airport'),
        ('organisation', '0106_organisationpeople_is_authorising_person_and_more'),
        ('user', '0028_alter_traveldocument_number_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mission_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Mission Number')),
                ('apacs_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='APACS Number')),
                ('callsign', models.CharField(blank=True, max_length=50, null=True, verbose_name='Callsign')),
                ('air_card_number', models.IntegerField(blank=True, null=True, verbose_name='AIR Card Number')),
                ('air_card_expiration', models.CharField(blank=True, max_length=4, null=True, verbose_name='AIR Card Expiration')),
                ('air_card_photo', models.FileField(blank=True, null=True, storage=app.storage_backends.AirCardPhotoStorage(), upload_to='')),
                ('is_confirmed', models.BooleanField(default=False, verbose_name='Is Confirmed?')),
                ('is_cancelled', models.BooleanField(default=False, verbose_name='Is Cancelled?')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('aircraft', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='missions', to='aircraft.aircrafthistory', verbose_name='Aircraft')),
                ('aircraft_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='missions', to='aircraft.aircrafttype', verbose_name='Aircraft Type')),
                ('assigned_mil_team_member', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assigned_missions', to='user.person', verbose_name='Assigned Mil Team Member')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_missions', to='user.person', verbose_name='Created By')),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='missions', to='organisation.organisation', verbose_name='Unit')),
                ('requesting_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_missions', to='user.person', verbose_name='Requesting Person')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='missions', to='handling.handlingrequesttype', verbose_name='Type')),
            ],
            options={
                'db_table': 'missions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MissionLeg',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_id', models.IntegerField(verbose_name='Sequence ID')),
                ('departure_datetime', models.DateTimeField(verbose_name='Departure Date')),
                ('departure_diplomatic_clearance', models.CharField(blank=True, max_length=100, null=True, verbose_name='Departure Diplomatic Clearance')),
                ('departure_aml_service', models.BooleanField(default=False, verbose_name='AML Service Required?')),
                ('arrival_datetime', models.DateTimeField(verbose_name='Arrival Date')),
                ('arrival_diplomatic_clearance', models.CharField(blank=True, max_length=100, null=True, verbose_name='Arrival Diplomatic Clearance')),
                ('arrival_aml_service', models.BooleanField(default=False, verbose_name='AML Service Required?')),
                ('pob_crew', models.IntegerField(verbose_name='POB Crew')),
                ('pob_pax', models.IntegerField(blank=True, null=True, verbose_name='POB Pax')),
                ('cob_lbs', models.IntegerField(blank=True, null=True, verbose_name='COB LBS')),
                ('callsign_override', models.CharField(blank=True, max_length=50, null=True, verbose_name='Callsign')),
                ('air_card_number', models.IntegerField(blank=True, null=True, verbose_name='AIR Card Number')),
                ('air_card_expiration', models.CharField(blank=True, max_length=4, null=True, verbose_name='AIR Card Expiration')),
                ('air_card_photo', models.FileField(blank=True, null=True, storage=app.storage_backends.AirCardPhotoStorage(), upload_to='')),
                ('is_confirmed', models.BooleanField(default=False, verbose_name='Is Confirmed?')),
                ('is_cancelled', models.BooleanField(default=False, verbose_name='Is Cancelled?')),
                ('remarks', models.CharField(blank=True, max_length=200, null=True, verbose_name='Remarks')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('arrival_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arrival_mission_legs', to='organisation.organisation', verbose_name='Arrival To')),
                ('arrival_sf_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='arrival_mission_legs', to='handling.handlingrequest', verbose_name='Arrival SFR')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_mission_legs', to='user.person', verbose_name='Created By')),
            ],
            options={
                'db_table': 'missions_legs',
                'ordering': ['mission', '-sequence_id'],
            },
        ),
        migrations.CreateModel(
            name='MissionLegPassengersPayload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.IntegerField(verbose_name='Identifier')),
                ('weight', models.IntegerField(verbose_name='Weight (lbs)')),
                ('note', models.CharField(blank=True, max_length=200, null=True, verbose_name='Note')),
                ('flight_leg', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='passengers_payloads', to='mission.missionleg', verbose_name='Mission Leg')),
                ('gender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mission_legs_passengers_payloads', to='user.persongender', verbose_name='Gender')),
            ],
            options={
                'db_table': 'missions_legs_payload_passengers',
            },
        ),
        migrations.CreateModel(
            name='MissionLegCrew',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary_contact', models.BooleanField(default=False, verbose_name='Primary Mission Contact')),
                ('can_update_mission', models.BooleanField(default=False, verbose_name='Can Update Mission?')),
                ('flight_leg', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mission_leg_crew', to='mission.missionleg', verbose_name='Flight Leg')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mission_legs_crew', to='user.person', verbose_name='Crew Member')),
                ('position', models.ForeignKey(default=1, on_delete=django.db.models.deletion.RESTRICT, to='handling.handlingrequestcrewmemberposition', verbose_name='Position')),
            ],
            options={
                'db_table': 'missions_legs_crew',
            },
        ),
        migrations.CreateModel(
            name='MissionLegCargoPayload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=200, verbose_name='Description')),
                ('length', models.IntegerField(verbose_name='Length')),
                ('width', models.IntegerField(verbose_name='Width')),
                ('height', models.IntegerField(verbose_name='Height')),
                ('weight', models.IntegerField(verbose_name='Weight (lbs)')),
                ('quantity', models.IntegerField(verbose_name='Quantity')),
                ('is_dg', models.BooleanField(default=False, verbose_name='Dangerous Goods')),
                ('note', models.CharField(blank=True, max_length=200, null=True, verbose_name='Notes')),
                ('flight_leg', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cargo_payloads', to='mission.missionleg', verbose_name='Mission Leg')),
            ],
            options={
                'db_table': 'missions_legs_payload_cargo',
            },
        ),
        migrations.AddField(
            model_name='missionleg',
            name='crew',
            field=models.ManyToManyField(related_name='mission_legs', through='mission.MissionLegCrew', to='user.person', verbose_name='Crew'),
        ),
        migrations.AddField(
            model_name='missionleg',
            name='departure_location',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='departure_mission_legs', to='organisation.organisation', verbose_name='Departure From'),
        ),
        migrations.AddField(
            model_name='missionleg',
            name='departure_sf_request',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='departure_mission_legs', to='handling.handlingrequest', verbose_name='Departure SFR'),
        ),
        migrations.AddField(
            model_name='missionleg',
            name='mission',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='legs', to='mission.mission', verbose_name='Mission'),
        ),
    ]
