# Generated by Django 4.0.3 on 2022-07-05 17:34

from django.db import migrations, models
from django.core.serializers import base, python
from django.core.management import call_command


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_unitofmeasurement_description_plural'),
    ]
    
    def load_fixture(apps, schema_editor):
        # Save the old _get_model() function
        old_get_model = python._get_model

        # Define new _get_model() function here, which utilizes the apps argument to
        # get the historical version of a model. This piece of code is directly stolen
        # from django.core.serializers.python._get_model, unchanged. However, here it
        # has a different context, specifically, the apps variable.
        def _get_model(model_identifier):
            try:
                return apps.get_model(model_identifier)
            except (LookupError, TypeError):
                raise base.DeserializationError(
                    "Invalid model identifier: '%s'" % model_identifier)

        # Replace the _get_model() function on the module, so loaddata can utilize it.
        python._get_model = _get_model

        try:
            # Call loaddata command
            call_command('loaddata', 'aircard_prefix.yaml',
                         app_label='core')
        finally:
            # Restore old _get_model() function
            python._get_model = old_get_model

    operations = [
        migrations.CreateModel(
            name='AirCardPrefix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_prefix', models.IntegerField(verbose_name='AIRcard Number Prefix')),
            ],
            options={
                'db_table': 'aircard_prefixes',
            },
        ),
        migrations.RunPython(load_fixture),
    ]
