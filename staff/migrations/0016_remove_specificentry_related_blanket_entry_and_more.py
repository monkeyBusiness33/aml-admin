# Generated by Django 4.2.6 on 2023-12-12 14:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0015_specificentry_related_blanket_entry_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='specificentry',
            name='related_blanket_entry',
        ),
        migrations.AddField(
            model_name='specificentry',
            name='replaces_other_entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replaces_other_entry', to='staff.blanketentry', verbose_name='Replaces Other Entry'),
        ),
        migrations.AddField(
            model_name='specificentry',
            name='replaces_own_entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replaces_own_entry', to='staff.blanketentry', verbose_name='Replaces Own Entry'),
        ),
    ]
