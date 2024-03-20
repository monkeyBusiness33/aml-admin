# Generated by Django 4.0.3 on 2023-07-14 09:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0011_alter_fuelagreement_end_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelagreement',
            name='superseded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='superseded_agreement', to='supplier.fuelagreement', verbose_name='Superseded By'),
        ),
    ]
