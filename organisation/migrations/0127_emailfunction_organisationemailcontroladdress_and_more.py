# Generated by Django 4.2.6 on 2023-12-15 18:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0033_usersettings"),
        ("core", "0056_commentreadstatus"),
        ("organisation", "0126_organisationdetails_updated_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailFunction",
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
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                (
                    "codename",
                    models.SlugField(
                        max_length=255, unique=True, verbose_name="Code Name"
                    ),
                ),
            ],
            options={
                "db_table": "organisations_email_control_functions",
            },
        ),
        migrations.CreateModel(
            name="OrganisationEmailControlAddress",
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
                    "email_address",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                        null=True,
                        verbose_name="Email Address",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        blank=True, max_length=200, null=True, verbose_name="Label"
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_control_addresses",
                        to="organisation.organisation",
                        verbose_name="Organisation",
                    ),
                ),
                (
                    "organisation_person",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_control_addresses",
                        to="organisation.organisationpeople",
                        verbose_name="Person",
                    ),
                ),
            ],
            options={
                "db_table": "organisations_email_control_addresses",
            },
        ),
        migrations.CreateModel(
            name="OrganisationEmailControlRule",
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
                ("is_cc", models.BooleanField(default=False, verbose_name="CC")),
                ("is_bcc", models.BooleanField(default=False, verbose_name="BCC")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "aml_email",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_control_rules",
                        to="organisation.organisationemailcontroladdress",
                        verbose_name="AML Email",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_control_rules",
                        to="user.person",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "email_function",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_control_rules",
                        to="organisation.emailfunction",
                        verbose_name="Email Function",
                    ),
                ),
                (
                    "recipient_based_airport",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={
                            "airport_details__isnull": False,
                            "details__type_id": 8,
                        },
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="airport_email_control_rules",
                        to="organisation.organisation",
                        verbose_name="Recipient Based Airport",
                    ),
                ),
                (
                    "recipient_based_country",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="country_email_control_rules",
                        to="core.country",
                        verbose_name="Recipient Based Country",
                    ),
                ),
                (
                    "recipient_organisation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organisation_email_control_rules",
                        to="organisation.organisation",
                        verbose_name="Recipient Organisation",
                    ),
                ),
            ],
            options={
                "db_table": "organisations_email_control_rules",
            },
        ),
    ]
