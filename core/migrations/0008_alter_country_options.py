# Generated by Django 4.0.3 on 2022-04-13 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_tag'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='country',
            options={'ordering': ['name']},
        ),
    ]
