# Generated by Django 4.0.3 on 2022-04-06 17:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_tag'),
        ('organisation', '0037_alter_operatordetails_contact_email_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'organisations_tags',
            },
        ),
        migrations.AddField(
            model_name='organisation',
            name='tags',
            field=models.ManyToManyField(related_name='organisations', through='organisation.OrganisationTag', to='core.tag'),
        ),
        migrations.AddField(
            model_name='organisationtag',
            name='organisation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisation.organisation'),
        ),
        migrations.AddField(
            model_name='organisationtag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.tag'),
        ),
    ]
