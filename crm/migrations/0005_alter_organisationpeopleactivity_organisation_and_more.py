# Generated by Django 4.0.3 on 2023-03-08 22:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0028_alter_traveldocument_number_and_more'),
        ('organisation', '0104_operatordetails_crew_weight_and_more'),
        ('crm', '0004_alter_organisationpeopleactivity_organisation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationpeopleactivity',
            name='organisation',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='crm_activity_log', to='organisation.organisation', verbose_name='Organisation'),
        ),
        migrations.AlterField(
            model_name='organisationpeopleactivity',
            name='person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='crm_activity_log', to='user.person', verbose_name='Person'),
        ),
    ]
