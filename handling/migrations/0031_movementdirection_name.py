# Generated by Django 4.0.3 on 2022-07-21 22:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0030_handlingrequestamendment_created_by_text_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='movementdirection',
            name='name',
            field=models.CharField(max_length=50, null=True, verbose_name='Name'),
        ),
    ]
