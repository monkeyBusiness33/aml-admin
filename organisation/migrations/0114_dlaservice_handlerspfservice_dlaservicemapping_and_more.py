# Generated by Django 4.2.6 on 2023-11-06 19:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pricing", "0090_remove_fuelagreementpricingformula_delivery_method_and_more"),
        ("organisation", "0113_alter_organisationcontactdetails_address_bcc_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DlaService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "khi_product_code",
                    models.CharField(max_length=200, verbose_name="KHI Product Code"),
                ),
                (
                    "is_spf_visible",
                    models.BooleanField(default=False, verbose_name="Is SPF Visible?"),
                ),
                (
                    "is_always_selected",
                    models.BooleanField(
                        default=False, verbose_name="Is Always Selected?"
                    ),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, verbose_name="Is Deleted?"),
                ),
            ],
            options={
                "db_table": "organisations_dla_services",
            },
        ),
        migrations.CreateModel(
            name="HandlerSpfService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "applies_after_minutes",
                    models.IntegerField(verbose_name="Applies After Minutes"),
                ),
                (
                    "applies_if_pax_onboard",
                    models.BooleanField(
                        default=False, verbose_name="Applies if Pax Onboard"
                    ),
                ),
                (
                    "applies_if_cargo_onboard",
                    models.BooleanField(
                        default=False, verbose_name="Applies if Cargo Onboard"
                    ),
                ),
                (
                    "source_supplier_invoice_ref",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        null=True,
                        verbose_name="Source Supplier Invoice Ref",
                    ),
                ),
                (
                    "source_supplier_pld_ref",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        null=True,
                        verbose_name="Source Supplier PLD Red",
                    ),
                ),
                (
                    "source_aml_order_ref",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        null=True,
                        verbose_name="Source AML Order Ref",
                    ),
                ),
                (
                    "dla_service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spf_services",
                        to="organisation.dlaservice",
                        verbose_name="DLA Service",
                    ),
                ),
                (
                    "handler",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spf_services",
                        to="organisation.organisation",
                        verbose_name="Ground Handler",
                    ),
                ),
            ],
            options={
                "db_table": "organisations_handlers_spf_services",
            },
        ),
        migrations.CreateModel(
            name="DlaServiceMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "charge_service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dla_service_mappings",
                        to="pricing.chargeservice",
                        verbose_name="Charge Service",
                    ),
                ),
                (
                    "dla_service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dla_service_mappings",
                        to="organisation.dlaservice",
                        verbose_name="DLA Service",
                    ),
                ),
            ],
            options={
                "db_table": "organisations_dla_services_mapping",
            },
        ),
        migrations.AddField(
            model_name="dlaservice",
            name="charge_services",
            field=models.ManyToManyField(
                blank=True,
                related_name="dla_services",
                through="organisation.DlaServiceMapping",
                to="pricing.chargeservice",
                verbose_name="Charge Services",
            ),
        ),
    ]
