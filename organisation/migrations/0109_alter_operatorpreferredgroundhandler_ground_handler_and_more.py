# Generated by Django 4.0.3 on 2023-09-29 13:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0108_merge_20230608_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operatorpreferredgroundhandler',
            name='ground_handler',
            field=models.ForeignKey(limit_choices_to={'handler_details__isnull': False}, on_delete=django.db.models.deletion.CASCADE, related_name='preferred_handler_operators', to='organisation.organisation', verbose_name='Preferred Ground Handler'),
        ),
        migrations.AlterField(
            model_name='operatorpreferredgroundhandler',
            name='organisation',
            field=models.ForeignKey(limit_choices_to={'operator_details__isnull': False}, on_delete=django.db.models.deletion.CASCADE, related_name='operator_preferred_handlers', to='organisation.organisation', verbose_name='Organisation'),
        ),
        migrations.AlterField(
            model_name='tripsupportclient',
            name='client',
            field=models.ForeignKey(limit_choices_to={'operator_details__isnull': False}, on_delete=django.db.models.deletion.CASCADE, related_name='trip_support_companies', to='organisation.organisation'),
        ),
    ]
