# Generated by Django 4.0.3 on 2023-10-25 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0090_remove_fuelagreementpricingformula_delivery_method_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuelindex',
            name='priority',
            field=models.PositiveSmallIntegerField(choices=[(3, 'Low'), (2, 'Medium'), (1, 'High'), (0, 'Urgent')], default=2, verbose_name='Priority'),
        ),
        migrations.AddField(
            model_name='fuelpricingmarketpld',
            name='priority',
            field=models.PositiveSmallIntegerField(choices=[(3, 'Low'), (2, 'Medium'), (1, 'High'), (0, 'Urgent')], default=2, verbose_name='Priority'),
        ),
    ]
