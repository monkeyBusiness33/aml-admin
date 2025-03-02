# Generated by Django 4.0.3 on 2022-07-05 17:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_aircardprefix'),
        ('handling', '0027_handlingservice_deleted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='handlingrequest',
            name='air_card_prefix',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='core.aircardprefix', verbose_name='AIR Card Prefix'),
        ),
    ]
