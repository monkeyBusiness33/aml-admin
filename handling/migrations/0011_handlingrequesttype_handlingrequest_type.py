# Generated by Django 4.0.3 on 2022-05-02 18:41

from django.db import migrations, models
import django.db.models.deletion




class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0010_handlingrequestamendment_created_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='HandlingRequestType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'db_table': 'handling_request_types',
            },
        ),
    ]
