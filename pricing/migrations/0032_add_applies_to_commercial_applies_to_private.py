# Generated by Django 4.0.3 on 2023-05-23 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0031_taxrule_applies_to_fees_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelagreementpricingformula',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='fuelagreementpricingformula',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
        migrations.AddField(
            model_name='fuelagreementpricingmanual',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='fuelagreementpricingmanual',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
        migrations.AddField(
            model_name='fuelpricingmarket',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='fuelpricingmarket',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
        migrations.AddField(
            model_name='supplierfuelfeerate',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='supplierfuelfeerate',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
        migrations.AddField(
            model_name='taxrule',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='taxrule',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
        migrations.AddField(
            model_name='taxruleexception',
            name='applies_to_commercial',
            field=models.BooleanField(default=False, verbose_name='Applies To Commercial'),
        ),
        migrations.AddField(
            model_name='taxruleexception',
            name='applies_to_private',
            field=models.BooleanField(default=True, verbose_name='Applies To Private'),
        ),
    ]
