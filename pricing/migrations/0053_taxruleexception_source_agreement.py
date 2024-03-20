# Generated by Django 4.0.3 on 2023-07-13 12:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0011_alter_fuelagreement_end_date'),
        ('pricing', '0052_merge_20230711_1543'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxruleexception',
            name='source_agreement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='associated_tax_exceptions', to='supplier.fuelagreement'),
        ),
    ]
