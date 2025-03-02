# Generated by Django 4.2.6 on 2023-11-06 19:08

from django.db import migrations, models
import shortuuid.main
import shortuuidfield.fields


class Migration(migrations.Migration):
    dependencies = [
        ("handling", "0097_alter_handlingrequestcargopayload_sync_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HandlingRequestSpf",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_reconciled",
                    models.BooleanField(default=False, verbose_name="Is Reconciled"),
                ),
                (
                    "reconciled_at",
                    models.DateTimeField(null=True, verbose_name="Reconciled At"),
                ),
            ],
            options={
                "db_table": "handling_requests_spf",
            },
        ),
        migrations.CreateModel(
            name="HandlingRequestSpfService",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_pre_ticked",
                    models.BooleanField(default=False, verbose_name="Is Pre Ticked"),
                ),
                ("was_taken", models.BooleanField(null=True, verbose_name="Was Taken")),
                (
                    "comments",
                    models.CharField(
                        max_length=500, null=True, verbose_name="Comments"
                    ),
                ),
            ],
            options={
                "db_table": "handling_requests_spf_services",
            },
        ),
        migrations.AlterField(
            model_name="handlingrequestcargopayload",
            name="sync_id",
            field=shortuuidfield.fields.ShortUUIDField(
                blank=True,
                default=shortuuid.main.ShortUUID.uuid,
                editable=False,
                max_length=22,
            ),
        ),
        migrations.AlterField(
            model_name="handlingrequestpassengerspayload",
            name="sync_id",
            field=shortuuidfield.fields.ShortUUIDField(
                blank=True,
                default=shortuuid.main.ShortUUID.uuid,
                editable=False,
                max_length=22,
            ),
        ),
        migrations.AlterField(
            model_name="handlingservice",
            name="always_included",
            field=models.BooleanField(
                default=False,
                help_text="This service will be automatically applied to each S&F Request",
                verbose_name="Always Included?",
            ),
        ),
    ]
