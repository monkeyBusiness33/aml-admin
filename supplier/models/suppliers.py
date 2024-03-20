from datetime import date, datetime, time, timedelta, timezone

from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import BooleanField, CharField, Case, Exists, ExpressionWrapper, F, OuterRef, Q, Subquery, \
    Value, When
from django.db.models.functions import Concat, TruncDate
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.utils.datatables_functions import get_fontawesome_icon
from organisation.models import Organisation, OrganisationContactDetails, OrganisationPeople
from pricing.models import PricingBacklogEntry, PrioritizedModel


class SupplierManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset().filter(
            Q(tags__pk__in=[2, 3])
        ).exclude(
            Q(details__type__pk=4)
        ).distinct()

        return qs


class Supplier(Organisation):

    objects = SupplierManager()

    class Meta:
        proxy = True


class FuelAgreementQuerySet(models.QuerySet):
    def backlog_entries(self, expired_only=False):
        """
        This query filters out data to be shown in the backlog. Note that the fields must match across
        all involved models, as these are merged using union().
        Also, note that in the future any data provided from a supplier via an integration will need
        to be excluded here, but at the moment no such integrations exist, so this could not be implemented.
        """
        supplier_has_emails = ExpressionWrapper(Exists(OrganisationContactDetails.objects.filter(
            organisation=OuterRef('supplier'), email_address__isnull=False
        )) | Exists(OrganisationPeople.objects.filter(
            Q(organisation=OuterRef('supplier')) & Q(contact_email__isnull=False) & ~Q(contact_email=''))
        ), output_field=BooleanField())

        # Exclude voided and already superseded agreements
        qs = self.filter(superseded_by__isnull=True, voided_at__isnull=True)

        if expired_only:
            qs = qs.filter(end_date__lt=date.today())
        else:
            qs = qs.filter(end_date__lte=date.today() + timedelta(days=28))

        return qs.only('pk', 'priority').annotate(
            type=Value('S'),
            name=Concat(Value('#'), F('pk'), Value(' '), F('aml_reference'),
                         output_field=CharField()),
            url_pk=F('pk'),
            supplier_pk=F('supplier_id'),
            supplier_name=Case(
                When(supplier__details__trading_name__isnull=False,
                     then=Concat(
                         'supplier__details__trading_name',
                         Value(' ('),
                         'supplier__details__registered_name',
                         Value(')'),
                         output_field=CharField())),
                default=F('supplier__details__registered_name')
            ),
            locations_str=Concat(
                StringAgg(
                    Concat(
                        F('pricing_formulae__location__airport_details__icao_code'),
                        Value(' / '),
                        F('pricing_formulae__location__airport_details__iata_code'),
                    ),
                    delimiter=', ',
                    distinct=True,
                    filter=Q(pricing_formulae__deleted_at__isnull=True),
                    default=Value('--')
                ),
                Value(', '),
                StringAgg(
                    Concat(
                        F('pricing_manual__location__airport_details__icao_code'),
                        Value(' / '),
                        F('pricing_manual__location__airport_details__iata_code'),
                    ),
                    delimiter=', ',
                    distinct=True,
                    filter=Q(pricing_manual__deleted_at__isnull=True),
                    default=Value('')
                ),
                output_field=CharField()
            ),
            expiry_date=TruncDate('end_date'),
            supplier_has_emails=supplier_has_emails,
        )


class FuelAgreement(PrioritizedModel, PricingBacklogEntry):
    supplier = models.ForeignKey("organisation.Organisation", verbose_name=_("Supplier"),
                                 limit_choices_to=Q(details__type_id__in=[2, 3, 4, 5, 7, 8, 13, 14])
                                                  | Q(airport_details__isnull=False)
                                                  | Q(handler_details__isnull=False) | Q(ipa_details__isnull=False)
                                                  | Q(oilco_details__isnull=False)
                                                  | Q(service_provider_locations__isnull=False),
                                 on_delete=models.CASCADE, related_name="agreements_where_supplier")
    supplier_agreement_reference = models.CharField(_("Supplier Agreement Reference"), max_length=50,
                                                    null=True, blank=True)
    aml_reference = models.CharField(_("AML Reference"), max_length=50, null=True, blank=True)
    aml_reference_legacy = models.CharField(_("AML Reference (Legacy)"), max_length=50, null=True, blank=True)
    aml_group_company = models.ForeignKey("organisation.Organisation", verbose_name=_("AML Group Company"),
                                          limit_choices_to={'details__type_id__in': [1000]},
                                          on_delete=models.CASCADE, related_name="agreements_with_suppliers")
    aml_is_agent = models.BooleanField(_("AML is Agent?"), default=False)
    start_date = models.DateField(_("Start Date"), auto_now=False, auto_now_add=False)
    end_date = models.DateTimeField(_("End Date"), auto_now=False, auto_now_add=False, null=True)
    valid_ufn = models.BooleanField(_("Valid UFN?"), default=False)
    is_active = models.BooleanField(_("Is Active?"), default=True)
    is_published = models.BooleanField(_("Is Published?"), default=False)
    is_reviewed = models.BooleanField(_("Is Reviewed?"), default=False)
    payment_terms_days = models.IntegerField(_("Payment Terms (Days)"), null=True)
    payment_terms_months = models.IntegerField(_("Payment Terms (Months)"), null=True)
    document = models.ForeignKey("organisation.OrganisationDocument", verbose_name=_("Document"),
                                 related_name='fuel_agreement_where_source_document',
                                 on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   on_delete=models.RESTRICT)
    review = models.ForeignKey("FuelAgreementReview", verbose_name=_("Review"),
                               on_delete=models.RESTRICT, null=True)
    comment = models.CharField(_("Comment"), max_length=500, null=True, blank=True)
    superseded_by = models.OneToOneField("FuelAgreement", verbose_name=_("Superseded By"),
                                         on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='superseded_agreement')
    voided_at = models.DateTimeField(_("Voided At"), auto_now=False, auto_now_add=False, null=True, blank=True)
    is_prepayment = models.BooleanField(_("Is Prepayment?"), default=False)
    deposit_required = models.BooleanField(_("Deposit Required?"), default=False)
    deposit_currency = models.ForeignKey("core.Currency", verbose_name=_("Deposit Currency"),
                                         on_delete=models.RESTRICT, null=True, blank=True)
    deposit_amount = models.DecimalField(_("Deposit Amount"), max_digits=12, decimal_places=2,
                                         null=True, blank=True)

    objects = FuelAgreementQuerySet.as_manager()

    class Meta:
        db_table = 'suppliers_fuel_agreements'

    def save(self, *args, **kwargs):
        self.update_end_date_time()
        super().save(*args, **kwargs)
        self.update_associated_fee_activity()

    def __str__(self):
        return f'#{str(self.pk)}' + (f': AML ref. {self.aml_reference}' if self.aml_reference else '')

    def get_absolute_url(self):
        return reverse_lazy('admin:fuel_agreement', kwargs={'pk': self.pk})

    @property
    def all_pricing(self):
        formula_locations = set(self.pricing_formulae.with_details().all())
        discount_locations = set(self.pricing_manual.with_details().all())

        return formula_locations.union(discount_locations)

    @property
    def all_pricing_location_pks(self):
        formula_locations = set(self.pricing_formulae.with_details().all().values_list('location__pk', flat=True))
        discount_locations = set(self.pricing_manual.with_details().all().values_list('location__pk', flat=True))

        return formula_locations.union(discount_locations)

    @property
    def all_pricing_locations(self):
        formula_locations = self.pricing_formulae.with_details().all().values_list('icao_iata', 'ipa_name')
        discount_locations = self.pricing_manual.with_details().all().values_list('icao_iata', 'ipa_name')

        return formula_locations.union(discount_locations)

    @property
    def aml_role(self):
        return 'Agent' if self.aml_is_agent else 'Reseller'

    @property
    def active_badge(self):
        if not self.is_active:
            return '<i class="lh-base fas fa-ban text-danger" data-bs-toggle="tooltip" data-bs-placement="top" title="Inactive"></i>'
        else:
            return '<i class="lh-base fas fa-check-circle text-success" data-bs-toggle="tooltip" data-bs-placement="top" title="Active"></i>'

    @property
    def deposit_currency_dict(self):
        if self.deposit_required:
            return {
                'code': self.deposit_currency.code
            }

    @property
    def datatable_str(self):
        return f'#{str(self.pk)}' + (f': {self.aml_reference}' if self.aml_reference else '')

    @property
    def display_fees(self):
        return self.associated_fees.with_location().with_details().filter(
            deleted_at__isnull=True, source_agreement_id=self.pk)

    @property
    def display_supplier_taxes(self):
        return self.associated_tax_exceptions.with_details().filter(
            parent_entry__isnull=True, deleted_at__isnull=True, source_agreement_id=self.pk)

    @property
    def document_description_icon(self):
        if self.document and self.document.description:
            desc_icon = get_fontawesome_icon(
                icon_name='info-circle',
                tooltip_text=self.document.description,
                tooltip_placement='right',
                tooltip_enable_html=True)

            return desc_icon

    @property
    def document_link(self):
        if self.document:
            return f"<a href={self.document.file.url}>{self.document.name}</a>"

    @property
    def end_date_str(self):
        if self.end_date is None:
            return

        if self.end_date.time() == time.fromisoformat('23:59:59.999999'):
            return self.end_date.strftime('%Y-%m-%d')
        else:
            return self.end_date.strftime('%Y-%m-%d %H:%M')

    @property
    def get_aml_reference(self):
        if self.aml_reference:
            return self.aml_reference + (f' / {self.aml_reference_legacy}' if self.aml_reference_legacy else '')
        else:
            return self.aml_reference_legacy

    @property
    def has_started(self):
        return self.start_date <= date.today()

    @property
    def is_expiring(self):
        return self.is_active and not (self.valid_ufn or self.end_date.date() > date.today() + timedelta(days=60))

    @property
    def is_voidable(self):
        return self.end_date >= datetime.now(timezone.utc)

    @property
    def payment_terms(self):
        if self.payment_terms_days:
            return f"{self.payment_terms_days} Day{'' if self.payment_terms_days == 1 else 's'}"
        elif self.payment_terms_months:
            return f"{self.payment_terms_months} Month{'' if self.payment_terms_months == 1 else 's'}"
        elif self.is_prepayment:
            return 'Prepayment'
        else:
            return 'Unspecified'

    @property
    def supplier_name(self):
        supplier_details = self.supplier.details

        if supplier_details.trading_name:
            return f'{supplier_details.trading_name} ({supplier_details.registered_name})'
        else:
            return supplier_details.registered_name

    @property
    def validity_range_str(self):
        end_date = 'Until Further Notice' if self.valid_ufn else self.end_date.date()

        return f'{self.start_date} - {end_date}'

    def get_fuel_types_at_location(self, location):
        formula_types = set(self.pricing_formulae.filter(deleted_at__isnull=True, location=location)
                            .values_list('fuel__name', flat=True).distinct())
        discount_types = set(self.pricing_manual.filter(deleted_at__isnull=True, location=location)
                             .values_list('fuel__name', flat=True).distinct())

        return formula_types.union(discount_types)

    def update_active_status_based_on_date(self):
        self.update_end_date_time()

        if self.has_started and (self.valid_ufn or self.end_date >= datetime.now(timezone.utc)):
            self.is_active = True
        else:
            self.is_active = False

    def update_associated_fee_activity(self):
        fees = self.associated_fees.filter(deleted_at__isnull=True)
        fees.update(
            price_active=self.is_active
        )

    def update_end_date_time(self):
        """
        When only date is specified, default to end of day (23:59:59.999999).
        Specific timestamp is only used for immediately voiding an agreement.
        """
        if type(self.end_date) == date:
            self.end_date = datetime.combine(self.end_date, time.fromisoformat('23:59:59.999999'), timezone.utc)


class FuelAgreementReview(models.Model):
    suppliers_fuel_agreement = models.ForeignKey("FuelAgreement", verbose_name=_("Fuel Agreement"),
                                       on_delete=models.CASCADE, related_name="reviews")
    assigned_at = models.DateTimeField(_("Assigned At"), auto_now=False, auto_now_add=False)
    assigned_to = models.ForeignKey("user.Person", verbose_name=_("Assigned To"),
                                   on_delete=models.RESTRICT, related_name="assigned_fuel_agreement_reviews")
    reviewed_at = models.DateTimeField(_("Reviewed At"), auto_now=False, auto_now_add=False,
                                       null=True)
    reviewed_by = models.ForeignKey("user.Person", verbose_name=_("Reviewed By"),
                                    null=True, on_delete=models.RESTRICT, related_name="reviewed_fuel_agreement_reviews")


    class Meta:
        db_table = 'suppliers_fuel_agreements_reviews'
