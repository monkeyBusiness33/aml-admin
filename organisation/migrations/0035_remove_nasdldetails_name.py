# Generated by Django 3.2.9 on 2022-03-29 21:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0034_hasdltype_nasdldetails'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nasdldetails',
            name='name',
        ),
    ]
