# Generated by Django 4.0.3 on 2022-11-04 14:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0001_initial'),
        ('pricing', '0014_supplieradditivepricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierfuelfeerate',
            name='source_agreement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='supplier.supplierfuelagreement', verbose_name='Source Agreement'),
        ),
    ]
