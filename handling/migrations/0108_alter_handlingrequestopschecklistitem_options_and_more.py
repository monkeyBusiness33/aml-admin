# Generated by Django 4.2.6 on 2023-11-21 12:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handling', '0107_merge_20231121_1212'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='handlingrequestopschecklistitem',
            options={'ordering': ['is_completed', 'checklist_item']},
        ),
        migrations.AlterModelOptions(
            name='permissions',
            options={'permissions': [('p_view', 'DoD Servicing: View section pages'), ('p_dod_comms', 'DoD Servicing: DoD Comms chat access'), ('p_sfr_export_data', 'DoD Servicing: S&F Request Data Export'), ('p_create', 'DoD Servicing: Create anything'), ('p_update', 'DoD Servicing: Update anything'), ('p_activity_log_view', 'DoD Servicing: View Activity Log'), ('p_dla_services_update', 'DoD Servicing: Create or Update DLA Services'), ('p_dla_services_view', 'DoD Servicing: View DLA Services'), ('p_spf_v2_reconcile', 'DoD Servicing: Reconcile SPF'), ('p_manage_sfr_ops_checklist_settings', 'DoD Servicing: Manage SFR Ops Checklist Settings')]},
        ),
        migrations.AlterModelOptions(
            name='sfropschecklistparameter',
            options={'ordering': ['category', 'description', 'url']},
        ),
    ]
