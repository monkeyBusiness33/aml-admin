# Generated by Django 4.0.3 on 2022-04-13 23:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0011_alter_person_aircraft_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonPronoun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject_pronoun', models.CharField(max_length=20, verbose_name='Subject Pronoun')),
                ('object_pronoun', models.CharField(max_length=20, verbose_name='Object Pronoun')),
            ],
            options={
                'db_table': 'people_personal_pronouns',
            },
        ),
        migrations.AddField(
            model_name='persondetails',
            name='personal_pronoun',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='user.personpronoun', verbose_name='Personal Pronoun'),
        ),
    ]
