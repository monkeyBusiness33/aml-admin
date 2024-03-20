from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import BooleanField, Case, CharField, Count, Exists, ExpressionWrapper, F, IntegerField, Max, \
    OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast, Concat
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from sql_util.utils import SubqueryCount

from core.templatetags.currency_uom_tags import custom_round_to_str
from core.utils.datatables_functions import get_datatable_text_with_tooltip
from organisation.models import OrganisationContactDetails, OrganisationPeople
from pricing.models import PricingBacklogEntry, PrioritizedModel


class FuelIndexQueryset(models.QuerySet):
    def with_status(self):
        return self.annotate(
            full_name=Concat(
                F('provider__details__trading_name'),
                Value(' ('),
                F('provider__details__registered_name'),
                Value(') '),
                F('name'),
            ),
            price_count=Count('details__prices'),
            valid_price_count=Count(Case(
                When(Q(details__prices__valid_to__gte=date.today()) | Q(details__prices__valid_ufn=True), then=1),
                output_field=IntegerField(),
            )),
            published_valid_price_count=Count(Case(
                When((Q(details__prices__valid_to__gte=date.today()) | Q(details__prices__valid_ufn=True)) &
                     Q(details__prices__is_published=True), then=1),
                output_field=IntegerField(),
            )),
            status=Case(
                When(price_count=0, then=Value(3)),
                When(valid_price_count=0, then=Value(2)),
                When(published_valid_price_count=0, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        )

class FuelIndex(PrioritizedModel):
    STATUS_DETAILS = {
        0: {'code': 0, 'detail': 'OK', 'background_color': '#c3e6cb', 'text_color': '#000'},
        1: {'code': 1, 'detail': 'OK (Unpublished)', 'background_color': '#c3e6cb', 'text_color': '#000'},
        2: {'code': 2, 'detail': 'Pricing Expired', 'background_color': '#e55353', 'text_color': '#fff'},
        3: {'code': 3, 'detail': 'No Pricing', 'background_color': '#000', 'text_color': '#fff'},
    }

    name = models.CharField(_("Name"), max_length=250)
    provider = models.ForeignKey("organisation.Organisation",
                                 verbose_name=_("Provider"),
                                 on_delete=models.CASCADE)
    is_active = models.BooleanField(_("Is Active?"), default=True)

    objects = FuelIndexQueryset.as_manager()

    class Meta:
        db_table = 'fuel_indices'
        ordering = ['name']

    def __str__(self):
        return f"{self.provider.full_repr} {self.name}"

    @property
    def active_badge(self):
        if not self.is_active:
            return '<i class="lh-base fas fa-ban text-danger" data-bs-toggle="tooltip" data-bs-placement="top" title="Inactive"></i>'
        else:
            return '<i class="lh-base fas fa-check-circle text-success" data-bs-toggle="tooltip" data-bs-placement="top" title="Active"></i>'

    @property
    def full_status(self):
        status_code = getattr(self, 'status', 0)
        return self.STATUS_DETAILS[status_code]

    def get_absolute_url(self):
        return reverse_lazy('admin:fuel_index_details', kwargs={'pk': self.pk})


class FuelIndexDetailsQueryset(models.QuerySet):
    def backlog_entries(self, expired_only=False):
        """
        This query filters out data to be shown in the backlog. Note that the fields must match across
        all involved models, as these are merged using union().
        Also, note that in the future any data provided from a supplier via an integration will need
        to be excluded here, but at the moment no such integrations exist, so this could not be implemented.
        """
        supplier_has_emails = ExpressionWrapper(Exists(OrganisationContactDetails.objects.filter(
            organisation=OuterRef('fuel_index__provider'), email_address__isnull=False)
        ) | Exists(OrganisationPeople.objects.filter(
            Q(organisation=OuterRef('fuel_index__provider')) & Q(contact_email__isnull=False) & ~Q(contact_email=''))
        ), output_field=BooleanField())

        qs = self.only('pk').annotate(
            priority=F('fuel_index__priority'),
            type=Value('I'),
            name=Concat(
                F('fuel_index__provider__details__trading_name'),
                Value(' ('),
                F('fuel_index__provider__details__registered_name'),
                Value(') '),
                F('fuel_index__name'),
                Value(' / '),
                Case(
                    When(Q(index_price_is_high=True), then=Value('High')),
                    When(Q(index_price_is_mean=True), then=Value('Mean')),
                    When(Q(index_price_is_low=True), then=Value('Low')),
                ),
                Case(
                    When(Q(index_period_is_daily=True), then=Value(' / Prior Day')),
                    When(Q(index_period_is_weekly=True), then=Value(' / Prior Week')),
                    When(Q(index_period_is_fortnightly=True), then=Value(' / Prior Fortnight')),
                    When(Q(index_period_is_monthly=True), then=Value(' / Prior Month')),
                ),
                output_field=CharField()
            ),
            url_pk=F('fuel_index__pk'),
            supplier_pk=F('fuel_index__provider_id'),
            supplier_name=Case(
                When(fuel_index__provider__details__trading_name__isnull=False,
                     then=Concat(
                         'fuel_index__provider__details__trading_name',
                         Value(' ('),
                         'fuel_index__provider__details__registered_name',
                         Value(')'),
                         output_field=CharField())),
                default=F('fuel_index__provider__details__registered_name')
            ),
            locations_str=Value(''),
            expiry_date=Max('prices__valid_to'),
            supplier_has_emails=supplier_has_emails,
        )

        if expired_only:
            qs = qs.filter(expiry_date__lt=date.today())
        else:
            qs = qs.filter(expiry_date__lte=date.today() + timedelta(days=1))

        return qs

    def with_status(self):
        return self.annotate(
            structure_str=Concat(
                Case(
                    When(Q(index_price_is_high=True), then=Value('High')),
                    When(Q(index_price_is_mean=True), then=Value('Mean')),
                    When(Q(index_price_is_low=True), then=Value('Low')),
                ),
                Case(
                    When(Q(index_period_is_daily=True), then=Value(' / Prior Day')),
                    When(Q(index_period_is_weekly=True), then=Value(' / Prior Week')),
                    When(Q(index_period_is_fortnightly=True), then=Value(' / Prior Fortnight')),
                    When(Q(index_period_is_monthly=True), then=Value(' / Prior Month')),
                ),
            ),
            full_name=Concat(
                F('fuel_index__provider__details__trading_name'),
                Value(' ('),
                F('fuel_index__provider__details__registered_name'),
                Value(') '),
                F('fuel_index__name'),
                Value(' / '),
                F('structure_str')
            ),
            price_count=Count('prices'),
            valid_price_count=Count(Case(
                When(Q(prices__valid_to__gte=date.today()) | Q(prices__valid_ufn=True), then=1),
                output_field=IntegerField(),
            )),
            published_valid_price_count=Count(Case(
                When((Q(prices__valid_to__gte=date.today()) | Q(prices__valid_ufn=True)) &
                     Q(prices__is_published=True), then=1),
                output_field=IntegerField(),
            )),
            status=Case(
                When(price_count=0, then=Value(3)),
                When(valid_price_count=0, then=Value(2)),
                When(published_valid_price_count=0, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        )


class FuelIndexDetails(models.Model):
    fuel_index = models.ForeignKey("FuelIndex", verbose_name=_("Fuel Index Details"),
                                   on_delete=models.CASCADE, related_name='details')
    index_price_is_mean = models.BooleanField(_("Price Is Mean?"), default=False)
    index_price_is_low = models.BooleanField(_("Price Is Low?"), default=False)
    index_price_is_high = models.BooleanField(_("Price Is High?"), default=False)
    index_period_is_daily = models.BooleanField(_("Period Is Daily?"), default=False)
    index_period_is_weekly = models.BooleanField(_("Period Is Weekly?"), default=False)
    index_period_is_fortnightly = models.BooleanField(_("Period Is Fortnightly?"), default=False)
    index_period_is_monthly = models.BooleanField(_("Period Is Monthly?"), default=False)

    objects = FuelIndexDetailsQueryset.as_manager()

    class Meta:
        db_table = 'fuel_indices_details'

    def __str__(self):
        return f"{self.fuel_index} / {self.structure_description}"

    @property
    def index_period(self):
        if self.index_period_is_daily:
            return 'D'
        if self.index_period_is_weekly:
            return 'W'
        if self.index_period_is_fortnightly:
            return 'F'
        if self.index_period_is_monthly:
            return 'M'

    @index_period.setter
    def index_period(self, value: str):
        if value.upper() == 'D':
            self.index_period_is_daily = True
            self.index_period_is_weekly = False
            self.index_period_is_fortnightly = False
            self.index_period_is_monthly = False
        elif value.upper() == 'W':
            self.index_period_is_daily = False
            self.index_period_is_weekly = True
            self.index_period_is_fortnightly = False
            self.index_period_is_monthly = False
        elif value.upper() == 'F':
            self.index_period_is_daily = False
            self.index_period_is_weekly = False
            self.index_period_is_fortnightly = True
            self.index_period_is_monthly = False
        elif value.upper() == 'M':
            self.index_period_is_daily = False
            self.index_period_is_weekly = False
            self.index_period_is_fortnightly = False
            self.index_period_is_monthly = True
        else:
            raise ValueError("Incorrect value passed to index_period setter. Has to be one of: 'D', 'W', 'F', 'M'")

    @property
    def index_period_repr(self):
        if self.index_period_is_daily:
            return 'Prior Day'
        if self.index_period_is_weekly:
            return 'Prior Week'
        if self.index_period_is_fortnightly:
            return 'Prior Fortnight'
        if self.index_period_is_monthly:
            return 'Prior Month'

    @property
    def index_price(self):
        if self.index_price_is_low:
            return 'L'
        if self.index_price_is_mean:
            return 'M'
        if self.index_price_is_high:
            return 'H'

    @index_price.setter
    def index_price(self, value: str):
        if value.upper() == 'L':
            self.index_price_is_low = True
            self.index_price_is_mean = False
            self.index_price_is_high = False
        elif value.upper() == 'M':
            self.index_price_is_low = False
            self.index_price_is_mean = True
            self.index_price_is_high = False
        elif value.upper() == 'H':
            self.index_price_is_low = False
            self.index_price_is_mean = False
            self.index_price_is_high = True
        else:
            raise ValueError("Incorrect value passed to index_price setter. Value has to be one of: 'L', 'M', 'H'")

    @property
    def index_price_repr(self):
        if self.index_price_is_low:
            return 'Low'
        if self.index_price_is_mean:
            return 'Mean'
        if self.index_price_is_high:
            return 'High'

    @property
    def structure_description(self):
        return f'{self.index_price_repr} / {self.index_period_repr}'


class FuelIndexPricingQueryset(models.QuerySet):
    def filter_by_date_for_calc(self, validity_date_utc):
        """
        This filter needs to include valid and expired pricing (to use in case no valid pricing is present).
        We are always excluding future pricing.
        """
        return self.annotate(
            is_expired=Case(
                When(Q(valid_to__lt=validity_date_utc) & Q(valid_ufn=False),
                     then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(Q(valid_from__lte=validity_date_utc))

    def latest_only(self):
        """
        Get the latest entry for each combination of FuelIndexDetails and Source Organisation.
        """
        price_group_subquery = self.filter(
            fuel_index_details=OuterRef('fuel_index_details'),
            source_organisation=OuterRef('source_organisation'),
        ).order_by('-valid_to_str')

        return self.annotate(
            pricing_entry_count=SubqueryCount('fuel_index_details__prices',
                                              filter=Q(source_organisation=OuterRef('source_organisation'))),
            latest_valid_to_str=Subquery(price_group_subquery.values('valid_to_str')[:1])
        ).filter(
            valid_to_str=F('latest_valid_to_str')
        )

    def with_specificity_score(self, pricing_supplier_pk):
        """
        Annotate specificity score for each applicable index pricing, that will be used to determine the rate used
        (rate with the highest score will be chosen, which generally means more specific).
        - Level 1: valid (if source matches supplier OR is primary): 1000, else: 0
        - Level 2: source organisation matches supplier: 100, else: 0
        - Level 3: valid (but not matching level 1 criteria) pricing: 10, else: 0
        - Level 4: primary pricing: 1, else: 0
        """
        return self.annotate(
            specificity_score=Case(
                When(is_expired=False,
                     then=Case(
                         When(Q(is_primary=True) | Q(source_organisation=Value(pricing_supplier_pk)), then=1000),
                         default=10
                     )),
                default=0
            ) + Case(
                When(Q(source_organisation=Value(pricing_supplier_pk)), then=100), default=0
            ) + Case(
                When(Q(is_primary=True), then=1), default=0
            )
        )

    def with_structure_details(self):
        return self.annotate(
            valid_to_str = Case(
                When(valid_to__isnull=True, then=Value('UFN')),
                default=Cast('valid_to', output_field=CharField()),
                output_field=CharField(),
            ),
            structure_str=Concat(
                Case(
                    When(Q(fuel_index_details__index_price_is_high=True), then=Value('High')),
                    When(Q(fuel_index_details__index_price_is_mean=True), then=Value('Mean')),
                    When(Q(fuel_index_details__index_price_is_low=True), then=Value('Low')),
                ),
                Case(
                    When(Q(fuel_index_details__index_period_is_daily=True), then=Value(' / Prior Day')),
                    When(Q(fuel_index_details__index_period_is_weekly=True), then=Value(' / Prior Week')),
                    When(Q(fuel_index_details__index_period_is_fortnightly=True), then=Value(' / Prior Fortnight')),
                    When(Q(fuel_index_details__index_period_is_monthly=True), then=Value(' / Prior Month')),
                ),
            ),)


class FuelIndexPricing(PricingBacklogEntry):
    fuel_index_details = models.ForeignKey("FuelIndexDetails", verbose_name=_("Fuel Index Details"),
                                           on_delete=models.CASCADE, related_name='prices', null=True)
    price = models.DecimalField(_("Price"), max_digits=12,
                                decimal_places=6)
    is_active = models.BooleanField(_("Is Active?"), default=True)
    is_published = models.BooleanField(_("Is Published?"), default=False)
    is_reviewed = models.BooleanField(_("Is Reviewed?"), default=False)
    valid_from = models.DateField(_("Valid From"), auto_now=False, auto_now_add=False)
    valid_to = models.DateField(_("Valid To"), auto_now=False, auto_now_add=False, null=True, blank=True)
    valid_ufn = models.BooleanField(_("Valid UFN?"), default=False)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"), on_delete=models.RESTRICT)
    source_document = models.ForeignKey("organisation.OrganisationDocument", verbose_name=_("Source Document"),
                                        on_delete=models.SET_NULL, db_column="source_document",
                                        null=True, blank=True)
    source_organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Source Organisation"),
                                            on_delete=models.RESTRICT, db_column="source_organisation",
                                            related_name="sourced_fuel_indices",
                                            limit_choices_to=Q(details__is_trading=True)
                                                             & (Q(tags__pk=2) | Q(details__type__in=[2, 5, 13, 17])
                                                                | Q(agreements_where_supplier__isnull=False)))
    review = models.ForeignKey("FuelIndexPricingReview", verbose_name=_("Review"),
                               on_delete=models.RESTRICT, null=True)
    is_primary = models.BooleanField(_("Is Primary?"), default=False)
    pricing_unit = models.ForeignKey("core.PricingUnit",
                                     verbose_name=_("Pricing Unit"),
                                     db_column='pricing_unit',
                                     on_delete=models.RESTRICT, )
    superseded_by = models.OneToOneField("FuelIndexPricing", verbose_name=_("Superseded By"),
                                         on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='superseded_pricing')

    objects = FuelIndexPricingQueryset.as_manager()

    class Meta:
        db_table = 'fuel_indices_pricing'

    def __str__(self):
        return f'{self.pk}'

    @property
    def active_badge(self):
        if not self.is_active:
            return '<i class="lh-base fas fa-ban text-danger" data-bs-toggle="tooltip"' \
                   ' data-bs-placement="top" title="Inactive"></i>'
        else:
            return '<i class="lh-base fas fa-check-circle text-success" data-bs-toggle="tooltip"' \
                   ' data-bs-placement="top" title="Active"></i>'

    @property
    def has_started(self):
        return self.valid_from <= date.today()

    @property
    def has_expired(self):
        return self.valid_to is not None and self.valid_to < date.today()

    @property
    def is_superseded(self):
        return self.superseded_by is not None

    @property
    def price_repr(self):
        return f"{self.price} {self.pricing_unit.unit_code}"

    @property
    def primary_badge(self):
        if not self.is_primary:
            return '<i class="lh-base fas fa-ban text-danger" data-bs-toggle="tooltip"' \
                   ' data-bs-placement="top" title="Non-primary"></i>'
        else:
            return '<i class="lh-base fas fa-check-circle text-success" data-bs-toggle="tooltip"' \
                   ' data-bs-placement="top" title="Primary"></i>'

    @property
    def validity(self):
        if self.valid_ufn:
            return f"{self.valid_from} - UFN"
        else:
            return f"{self.valid_from} - {self.valid_to}"

    def get_pricing_datatable_str(self):
        """
        Return a representation for datatables, rounded to two decimals,
        with a tooltip showing the entire number where applicable.
        """
        formatted_pricing = '{:.2f}'.format(self.price)

        if Decimal(formatted_pricing) != self.price:
            formatted_pricing = get_datatable_text_with_tooltip(
                text=f'{formatted_pricing} {self.pricing_unit.unit_code}',
                span_class='pricing-tooltip',
                tooltip_text=f'{custom_round_to_str(self.price, 2, 6, normalize_decimals=True)}'
                             f' {self.pricing_unit.unit_code}',
                tooltip_enable_html=True
            )
        else:
            formatted_pricing += f' {self.pricing_unit.unit_code}'

        return formatted_pricing

    def update_active_status_based_on_date(self):
        if self.has_started and (self.valid_ufn or self.valid_to >= date.today()):
            self.is_active = True
        else:
            self.is_active = False


class FuelIndexPricingReview(models.Model):
    fuel_indices_pricing = models.ForeignKey("FuelIndexPricing", verbose_name=_("Fuel Index Pricing"),
                                             on_delete=models.CASCADE, related_name="reviews")
    assigned_at = models.DateTimeField(_("Assigned At"), auto_now=False, auto_now_add=False)
    assigned_to = models.ForeignKey("user.Person", verbose_name=_("Assigned To"),
                                    on_delete=models.RESTRICT, related_name="assigned_fuel_index_pricing_reviews")
    reviewed_at = models.DateTimeField(_("Reviewed At"), auto_now=False, auto_now_add=False,
                                       null=True)
    reviewed_by = models.ForeignKey("user.Person", verbose_name=_("Reviewed By"),
                                    null=True, on_delete=models.RESTRICT,
                                    related_name="reviewed_fuel_index_pricing_reviews")

    class Meta:
        db_table = 'fuel_indices_pricing_reviews'
