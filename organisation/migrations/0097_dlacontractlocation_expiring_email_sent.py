# Generated by Django 4.0.3 on 2022-09-30 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0096_alter_dlacontractlocation_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dlacontractlocation',
            name='expiring_email_sent',
            field=models.BooleanField(default=False, verbose_name='Expiring Email Sent'),
        ),
    ]
