# Generated by Django 4.2.7 on 2023-12-04 13:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0033_usersettings'),
        ('staff', '0007_alter_blanketentry_action_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='blanketentry',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.person', verbose_name='Updated By'),
        ),
        migrations.AddField(
            model_name='blanketentryoverride',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.person', verbose_name='Updated By'),
        ),
        migrations.AddField(
            model_name='specificentry',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.person', verbose_name='Updated By'),
        ),
    ]
