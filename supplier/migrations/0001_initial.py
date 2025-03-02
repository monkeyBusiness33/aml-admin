# Generated by Django 4.0.3 on 2022-11-04 14:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organisation', '0098_ipalocation_location_email_and_more'),
        ('user', '0024_user_last_token_sent_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('organisation.organisation',),
        ),
        migrations.CreateModel(
            name='SupplierFuelAgreement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreements_where_supplier', to='supplier.supplier', verbose_name='Supplier')),
                ('supplier_agreement_reference', models.CharField(blank=True, max_length=50, null=True, verbose_name='Supplier Agreement Reference')),
                ('aml_reference', models.CharField(blank=True, max_length=50, null=True, verbose_name='AML Reference')),
                ('aml_reference_legacy', models.CharField(blank=True, max_length=50, null=True, verbose_name='AML Reference (Legacy)')),
                ('aml_group_company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreements_with_suppliers', to='organisation.organisation', verbose_name='AML Group Company')),
                ('aml_is_agent', models.BooleanField(default=False, verbose_name='AML is Agent?')),
                ('start_date', models.DateField(verbose_name='Start Date')),
                ('end_date', models.DateField(null=True, verbose_name='End Date')),
                ('valid_ufn', models.BooleanField(default=False, verbose_name='Valid UFN?')),
                ('active', models.BooleanField(default=True, verbose_name='Is Active?')),
                ('payment_terms_days', models.IntegerField(null=True, verbose_name='Payment Terms (Days)')),
                ('payment_terms_months', models.IntegerField(null=True, verbose_name='Payment Terms (Months)')),
                ('document', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisation.organisationdocument', verbose_name='Document')),
                ('comment', models.CharField(blank=True, max_length=500, null=True, verbose_name='Comments')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='user.person', verbose_name='Updated By')),
            ],
            options={
                'db_table': 'suppliers_fuel_agreements',
            },
        ),
    ]
