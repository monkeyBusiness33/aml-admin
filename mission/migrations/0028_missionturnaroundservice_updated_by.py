# Generated by Django 4.0.3 on 2023-08-25 17:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0031_remove_user_is_superuser'),
        ('mission', '0027_alter_mission_aircraft'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionturnaroundservice',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.person', verbose_name='Updated By'),
        ),
    ]
