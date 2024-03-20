# Generated by Django 4.0.3 on 2023-03-01 17:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0024_user_last_token_sent_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonGender',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, verbose_name='Name')),
            ],
            options={
                'db_table': 'people_gender',
            },
        ),
    ]
