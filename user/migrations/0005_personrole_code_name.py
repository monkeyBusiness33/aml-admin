# Generated by Django 3.2.9 on 2022-01-29 16:57

from django.db import migrations, models


def populate_code_name(apps, schema_editor):
    import random
    import string
    PersonRole = apps.get_model('user', 'PersonRole')
    for row in PersonRole.objects.filter(code_name__isnull=True):
        row.code_name = ''.join(random.choice(string.ascii_letters)
                                for x in range(3)).upper()
        row.save()

class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_merge_0002_customnotification_0003_personrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='personrole',
            name='code_name',
            field=models.CharField(max_length=3, null=True, unique=True, verbose_name='Code Name'),
        ),
        migrations.RunPython(populate_code_name,
                             reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='personrole',
            name='code_name',
            field=models.CharField(max_length=3, unique=True, verbose_name='Code Name'),
        )
    ]
