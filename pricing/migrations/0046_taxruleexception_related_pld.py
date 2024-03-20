# Generated by Django 4.0.3 on 2023-06-30 14:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0045_taxruleexception_parent_entry_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxruleexception',
            name='related_pld',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='associated_tax_exceptions', to='pricing.fuelpricingmarketpld'),
        ),
    ]
