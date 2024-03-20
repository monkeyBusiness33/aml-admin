# Generated by Django 4.0.3 on 2023-06-13 14:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0108_merge_20230608_1617'),
        ('supplier', '0008_alter_fuelagreement_document'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fuelagreement',
            name='aml_group_company',
            field=models.ForeignKey(limit_choices_to={'details__type_id__in': [1000]}, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_with_suppliers', to='organisation.organisation', verbose_name='AML Group Company'),
        ),
        migrations.AlterField(
            model_name='fuelagreement',
            name='supplier',
            field=models.ForeignKey(limit_choices_to={'details__type_id__in': [2, 3, 5, 8, 13, 14]}, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_where_supplier', to='organisation.organisation', verbose_name='Supplier'),
        ),
    ]
