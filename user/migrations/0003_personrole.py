# Generated by Django 3.2.9 on 2022-01-29 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0004_alter_organisationpeople_role'),
    ]

    state_operations = [
        migrations.CreateModel(
            name='PersonRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'db_table': 'people_roles',
            },
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
