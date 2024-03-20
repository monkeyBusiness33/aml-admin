import pytz
from datetime import datetime

from django.utils.functional import cached_property
from timezonefinder import TimezoneFinder

from django.apps import apps
from django.contrib.postgres.expressions import ArraySubquery
from django.db import models
from django.contrib.postgres.aggregates import StringAgg
from django.dispatch import receiver
from django.db.models import Case, CharField, Exists, F, Func, IntegerField, Max, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Concat
from django.db.models.signals import post_save
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from app.storage_backends import OrganisationsLogosStorage
from core.forms import phone_regex_validator
from core.utils.datatables_functions import get_colored_circle, get_datatable_badge, get_fontawesome_icon
from organisation.models.ops_details import OrganisationOpsDetails


class OrganisationTypeQuerySet(models.QuerySet):
    def secondary_types(self):
        """
        Include all org types that have detail edit pages, except
         - Fuel Resellers and Agents (their detail pages only allow to change the main type)
         - NASDLs (these don't mix with other orgs)
        """
        return self.filter(
            Q(pk__in=[1, 3, 4, 5, 11, 14])
        )


class OrganisationType(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    is_fuel_end_user = models.BooleanField(_("Is Fuel End User?"), default=False)

    objects = OrganisationTypeQuerySet.as_manager()

    class Meta:
        db_table = 'organisations_types'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}'

    def get_edit_url_for_org(self, org):
        if self.pk == 1:
            return reverse_lazy('admin:aircraft_operators_edit', kwargs={'organisation_id': org.pk})
        elif self.pk in [2, 13]:
            return reverse_lazy('admin:fuel_reseller_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 3:
            return reverse_lazy('admin:ground_handler_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 4:
            return reverse_lazy('admin:ipa_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 5:
            return reverse_lazy('admin:oilco_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 11:
            return reverse_lazy('admin:trip_support_company_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 14:
            return reverse_lazy('admin:service_provider_edit', kwargs={'organisation_id': org.pk})
        elif self.pk == 1002:
            return reverse_lazy('admin:nasdl_edit', kwargs={'organisation_id': org.pk})
        else:
            return None


class OrganisationManager(models.QuerySet):
    def include_departments(self):
        qs = self.annotate(
            top_level_parent_id=Case(
                When(details__department_of__details__department_of__details__department_of__isnull=False,
                     then=F('details__department_of__details__department_of')),
                When(details__department_of__details__department_of__isnull=False,
                     then=F('details__department_of__details__department_of')),
                When(details__department_of__isnull=False, then=F('details__department_of')),
                default=None,
                output_field=IntegerField(),
            )
        )

        return qs

    def aircraft_operator(self):
        return self.filter(operator_details__isnull=False)

    def fuel_reseller(self):
        return self.filter(details__type_id=2)

    def handling_agent(self):
        return self.filter(handler_details__isnull=False)

    def ipa(self):
        return self.filter(ipa_details__isnull=False)

    def oilco(self):
        return self.filter(oilco_details__isnull=False)

    def airport(self):
        return self.filter(details__type_id=8, airport_details__isnull=False)

    def trip_support_company(self):
        return self.filter(Q(details__type_id=11) | Q(trip_support_clients__isnull=False)).distinct()

    def fuel_agent(self):
        return self.filter(details__type_id=13)

    def fuel_seller(self):
        fuel_pricing_market_model = apps.get_model('pricing.FuelPricingMarket')
        active_market_pricing_qs = fuel_pricing_market_model.objects.filter(
            Q(supplier_pld_location__pld__supplier=OuterRef('pk'))
            & Q(deleted_at__isnull=True) & Q(price_active=True)
        )

        return self.filter(Q(details__type_id__in=[2, 13]) | Q(tags__pk=2)
                           | Exists(active_market_pricing_qs)
                           | Q(agreements_where_supplier__isnull=False)).distinct()

    def service_provider(self):
        return self.filter(Q(details__type_id=14) | Q(service_provider_locations__isnull=False)).distinct()

    def airport_based_organisations(self, airport_id):
        return self.filter(
            Q(service_provider_locations__delivery_location_id=airport_id) |
            Q(addresses__airport_id=airport_id),
        ).exclude(
            Q(handler_details__isnull=False)
            | Q(ipa_details__isnull=False)
            | (Q(details__type__id=8) & Q(airport_details__isnull=False))
        )

    def dao(self):
        return self.filter(details__type_id=1001)

    def nasdl(self):
        return self.filter(details__type_id=1002, nasdl_details__isnull=False)

    def aircraft_operator_military(self):
        """
        Organisations whom can be serviced as DoD
        :return: QuerySet
        """
        return self.filter(operator_details__isnull=False, operator_details__type_id__in=[13, 14, 15, 16, 17])

    def handling_request_locations(self):
        return self.filter(
            (Q(details__type_id=8) & Q(airport_details__isnull=False)) |
            (Q(details__type_id=1002) & Q(nasdl_details__isnull=False))
        )

    def fuelling_ipa_or_handler(self):
        return self.filter(
            Q(handler_details__isnull=False) | Q(ipa_details__isnull=False)
        )

    def sanctioned(self):
        return self.filter(is_sanctioned_ofac=True, details__isnull=False)

    def handling_agent_with_airport_details(self):
        return self.filter(handler_details__isnull=False).annotate(icao_iata=Case(
                When(Q(handler_details__airport__airport_details__iata_code__isnull=True)
                     | Q(handler_details__airport__airport_details__iata_code=''), then=F(
                    'handler_details__airport__airport_details__icao_code')),
                When(Q(handler_details__airport__airport_details__icao_code__isnull=True)
                     | Q(handler_details__airport__airport_details__icao_code=''), then=F(
                    'handler_details__airport__airport_details__iata_code')),
                default=Concat(
                    'handler_details__airport__airport_details__icao_code',
                    Value(' / '),
                    'handler_details__airport__airport_details__iata_code',
                    output_field=CharField()
                )))

    def with_market_pld_details(self, supplier_pk):
        fuel_pricing_market_model = apps.get_model('pricing.FuelPricingMarket')
        active_market_pricing_qs = fuel_pricing_market_model.objects.filter(
            Q(supplier_pld_location__location=OuterRef('pk'))
            & Q(supplier_pld_location__pld__supplier=supplier_pk)
            & Q(deleted_at__isnull=True) & Q(price_active=True)
        )

        return self.annotate(
            active_market_pricing_plds=ArraySubquery(
                active_market_pricing_qs.values('supplier_pld_location__pld').distinct()
            ),
            latest_valid_to=Max("fuel_pricing_market_plds_at_location__fuel_pricing_market__valid_to_date"),
            latest_expiry_date=Func(
                F('latest_valid_to'),
                Value('yyyy-MM-dd'),
                function='to_char',
                output_field=CharField()
            ),
            fuel_types=ArraySubquery(active_market_pricing_qs.values('fuel__name').distinct())
        ).filter(
            Exists(Subquery(active_market_pricing_qs))
        )

    def billable_orgs_for_pld(self, pld):
        from pricing.models import FuelPricingMarketPldLocation

        return self.filter(
            (Q(fuel_pricing_market_plds_where_is_supplier=pld)
             & Exists(FuelPricingMarketPldLocation.objects.filter(pld=pld, billable_organisation__isnull=True)))
            | Exists(FuelPricingMarketPldLocation.objects.filter(pld=pld, billable_organisation=OuterRef('pk')))
        ).distinct()


class Organisation(models.Model):
    details = models.OneToOneField("organisation.OrganisationDetails",
                                   related_name='organisation_current',
                                   on_delete=models.CASCADE)
    is_sanctioned_ofac = models.BooleanField(_("Is Sanctioned OFAC?"), default=False)
    ofac_latest_update = models.DateTimeField(auto_now=False, auto_now_add=False, null=True)
    people = models.ManyToManyField("user.Person", through='organisation.OrganisationPeople',
                                    related_name='organisations')
    ipa_locations = models.ManyToManyField("organisation.Organisation",
                                           related_name='ipas_here',
                                           through='organisation.IpaLocation')
    trip_support_clients = models.ManyToManyField("organisation.Organisation",
                                                    related_name='trip_support_clients_reverse',
                                                    through='organisation.TripSupportClient')
    dao_countries = models.ManyToManyField("core.Country",
                                           through='organisation.DaoCountry')
    tags = models.ManyToManyField("core.Tag", through='organisation.OrganisationTag',
                                  blank=True, related_name='organisations')
    aircraft_types = models.ManyToManyField("aircraft.AircraftType",
                                            verbose_name=_("Types Operated"),
                                            through='organisation.OrganisationAircraftType',
                                            blank=True, related_name='organisations',)
    oilco_fuel_types = models.ManyToManyField("core.FuelType",
                                              verbose_name=_("Fuel Types Produced"),
                                              through='organisation.OilcoFuelType',
                                              blank=True, related_name='oilco_organisations',)
    dla_contracted_locations = models.ManyToManyField("organisation.Organisation",
                                                      related_name='dla_contracted_suppliers',
                                                      through='organisation.DLAContractLocation',
                                                      through_fields=('supplier', 'location'))

    objects = OrganisationManager().as_manager()

    class Meta:
        ordering = ['details__registered_name']
        db_table = 'organisations'
        permissions = [
            ('add_aircraft_operator', 'Add Aircraft Operator'),
            ('view_aircraft_operator', 'View Aircraft Operator Organisation'),
            ('view_airport', 'View Airport Organisation'),
            ('view_dao', 'View DAO (Defense Attache Offices)'),
            ('view_fuel_reseller', 'View Fuel Reseller'),
            ('change_fuel_reseller', 'Edit (change) Fuel Reseller'),
            ('change_ipa', 'Edit (change) Into-Plane Agent (IPA)'),
            ('change_handler', 'Edit (change) Ground Handler'),
            ('change_oilco', 'Edit (change) Oil Company (OilCo)'),
            ('change_nasdl', 'Edit (change) Non-Airport Location (NASDL)'),
            ('change_service_provider', 'Edit (change) Service Provider'),
            ('change_trip_support_company', 'Edit (change) Trip Support Company'),
        ]

    @property
    def has_active_market_pricing(self):
        fuel_pricing_market_model = apps.get_model('pricing.FuelPricingMarket')
        active_market_pricing_qs = fuel_pricing_market_model.objects.filter(
            Q(supplier_pld_location__pld__supplier=self.pk)
            & Q(deleted_at__isnull=True) & Q(price_active=True)
        )

        return active_market_pricing_qs.exists()

    @property
    def has_missing_org_types(self):
        return any(self.missing_org_type_urls.values())

    @property
    def missing_org_type_urls(self):
        # NASDLs excluded on purpose (don't mix with other orgs)
        return {
            'Aircraft Operator': reverse('admin:aircraft_operators_edit',
                                         kwargs={'organisation_id': self.pk})
            if not bool(getattr(self, 'operator_details', None)) else None,
            'Ground Handler': reverse('admin:ground_handler_edit',
                                      kwargs={'organisation_id': self.pk})
            if not bool(getattr(self, 'handler_details', None)) else None,
            'Fuel Seller': reverse('admin:add_fuel_seller_tag',
                                   kwargs={'pk': self.pk})
            if not bool(self.sells_fuel) else None,
            'Into-Plane Agent': reverse('admin:ipa_edit',
                                        kwargs={'organisation_id': self.pk})
            if not bool(getattr(self, 'ipa_details', None)) else None,
            'Oil Company': reverse('admin:oilco_edit',
                                   kwargs={'organisation_id': self.pk})
            if not bool(getattr(self, 'oilco_details', None)) else None,
            'Service Provider': reverse('admin:service_provider_edit',
                                        kwargs={'organisation_id': self.pk})
            if not self.provides_services else None,
            'Trip Support Company': reverse('admin:trip_support_company_edit',
                                            kwargs={'organisation_id': self.pk})
            if not self.provides_trip_support else None,
        }

    def get_absolute_url(self):
        if self.details.is_missing_details:
            return self.get_absolute_edit_url()

        if self.details.type_id == 1:
            return reverse_lazy('admin:aircraft_operator', kwargs={'pk': self.pk})
        elif self.details.type_id in [2, 13]:
            return reverse_lazy('admin:fuel_reseller', kwargs={'pk': self.pk})
        elif self.details.type_id == 3:
            return reverse_lazy('admin:ground_handler', kwargs={'pk': self.pk})
        elif self.details.type_id == 4:
            return reverse_lazy('admin:ipa', kwargs={'pk': self.pk})
        elif self.details.type_id == 5:
            return reverse_lazy('admin:oilco', kwargs={'pk': self.pk})
        elif self.details.type_id == 8:
            return reverse_lazy('admin:airport', kwargs={'pk': self.pk})
        elif self.details.type_id == 11:
            return reverse_lazy('admin:trip_support_company', kwargs={'pk': self.pk})
        elif self.details.type_id == 14:
            return reverse_lazy('admin:service_provider', kwargs={'pk': self.pk})
        elif self.details.type_id == 1001:
            return reverse_lazy('admin:dao', kwargs={'pk': self.pk})
        elif self.details.type_id == 1002:
            return reverse_lazy('admin:nasdl', kwargs={'pk': self.pk})
        else:
            return reverse_lazy('admin:organisation_details', kwargs={'pk': self.pk})

    def get_absolute_edit_url(self):
        if self.details.type.id == 1:
            return reverse_lazy('admin:aircraft_operators_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id in [2, 13]:
            return reverse_lazy('admin:fuel_reseller_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 3:
            return reverse_lazy('admin:ground_handler_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 4:
            return reverse_lazy('admin:ipa_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 5:
            return reverse_lazy('admin:oilco_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 11:
            return reverse_lazy('admin:trip_support_company_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 14:
            return reverse_lazy('admin:service_provider_edit', kwargs={'organisation_id': self.pk})
        elif self.details.type.id == 1002:
            return reverse_lazy('admin:nasdl_edit', kwargs={'organisation_id': self.pk})
        else:
            return None

    def save(self, *args, **kwargs):
        if not self.pk:
            details = self.details
            organisation_id_offset_min = int(f'{details.type.id}00000')
            organisation_id_offset_max = organisation_id_offset_min + 99999

            latest_db_id = Organisation.objects.filter(
                id__gte=organisation_id_offset_min,
                id__lte=organisation_id_offset_max,
            ).aggregate(Max('id'))['id__max']

            if latest_db_id:
                new_id = latest_db_id + 1
            else:
                new_id = organisation_id_offset_min

            self.pk = new_id
        super().save(*args, **kwargs)
        OrganisationOpsDetails.objects.get_or_create(organisation=self)

    def __str__(self):
        return f'{self.id}'

    @property
    def credit_exposure(self):
        """
        Determines whether 'credit exposure' section should be applied on organisation details page.
        """
        return self.details.type.pk in [1, 2, 3, 4, 11, 13, 14]

    @cached_property
    def provides_services(self):
        return self.details.type.pk == 14 or self.service_provider_locations.exists()

    @cached_property
    def provides_trip_support(self):
        return self.details.type.pk == 11 or self.trip_support_clients.exists()

    @cached_property
    def sells_fuel(self):
        return any([self.details.type.pk in [2, 13],
                    2 in self.tags.values_list('pk', flat=True),
                    self.has_active_market_pricing,
                    self.agreements_where_supplier.exists()])

    @property
    def tiny_repr(self):
        """
        Returns "tiny representation" to display organisation name
        :return:
        """
        if self.details.type_id == 8:
            return self.airport_details.icao_code
        else:
            return self.details.registered_name

    @cached_property
    def short_repr(self):
        """
        Returns "short representation" to display organisation name
        :return:
        """
        if self.details.type_id == 8:
            return self.airport_details.icao_iata
        else:
            return self.details.registered_name

    @property
    def trading_and_registered_name(self):
        if self.details.trading_name:
            return f'{self.details.registered_name} T/A {self.details.trading_name}'
        return self.details.registered_name

    @property
    def trading_or_registered_name(self):
        """
        This property returns organisation's trading name or registered_name as fallback
        """
        if self.details.trading_name:
            return self.details.trading_name
        return self.details.registered_name

    @property
    def full_repr(self):
        """
        Returns "full representation" to display organisation name, vary on organisation type
        :return:
        """
        details = getattr(self, 'details', None)
        if details:
            if details.type_id in (4, 17) and details.trading_name:
                return f'{details.trading_name} ({details.registered_name})'
            if details.type_id == 8:
                return f'{details.registered_name} ({self.airport_details.icao_iata})'
            return details.registered_name

    @property
    def airport_based_organisations(self):
        '''
        Returns organisations based in this organisation location
        '''
        return Organisation.objects.airport_based_organisations(self.pk)

    @property
    def based_airports(self) -> list:
        """
        Property returns airport where is organisation based are.
        :return:
        """
        if self.details.type_id == 3:
            return [self.handler_details.airport]
        if self.details.type_id == 4:
            locations = Organisation.objects.filter(
                Q(ipa_locations_here__organisation_id=self) |
                Q(service_provider_locations__delivery_location_id=self)
            )
            return list(locations)

    def get_email_address(self) -> list:
        """
        Returns email addresses for current organisation
        :return:
        """
        email_addresses = []

        if self.details.type_id == 3:
            handler_details = getattr(self, 'handler_details', None)
            if handler_details.contact_email and handler_details.contact_email != '':
                email_addresses.append(handler_details.contact_email)
            if handler_details.ops_email and handler_details.ops_email != '':
                email_addresses.append(handler_details.ops_email)

        # Fetch Email Addresses from Organisation Addresses
        address_emails = self.addresses.filter(
            is_primary_address=True,
        ).exclude(
            Q(email__isnull=True) | Q(email='')
        ).values_list('email', flat=True)

        email_addresses += list(address_emails)
        return email_addresses

    @property
    def is_military(self):
        operator_details = getattr(self, 'operator_details', None)
        if operator_details and operator_details.type.operates_military_flights == True:
            return True
        else:
            return False

    @property
    def longitude(self):
        if self.details.type_id == 8 and hasattr(self, 'airport_details'):
            return self.airport_details.longitude
        if self.details.type_id == 1002 and hasattr(self, 'nasdl_details'):
            return self.nasdl_details.longitude

    @property
    def latitude(self):
        if self.details.type_id == 8 and hasattr(self, 'airport_details'):
            return self.airport_details.latitude
        if self.details.type_id == 1002 and hasattr(self, 'nasdl_details'):
            return self.nasdl_details.latitude

    @property
    def is_lat_lon_available(self):
        return all([self.longitude, self.latitude])

    @property
    def authorising_person_role_name(self):
        if self.pk == 100001 or self.details.department_of_id == 100001:
            role_name = 'Resource Advisor'
        else:
            role_name = 'Authorizing Officer'
        return role_name

    @property
    def operational_status(self):
        status_vars = {
            'code': '',
            'text': '',
            'text_color': '',
            'badge_bg': '',
            'header_color': '',
        }

        if not self.details.is_trading:
            status_vars['code'] = 'ceased_trading'
            status_vars['text'] = 'Ceased Trading'
            status_vars['badge_bg'] = 'bg-grey'
            status_vars['text_color'] = 'organisation-ceased-trading'
            status_vars['header_color'] = 'text-black-50'

        if self.is_sanctioned_ofac:
            status_vars['code'] = 'sanctioned'
            status_vars['text'] = 'Sanctioned'
            status_vars['badge_bg'] = 'bg-danger'
            status_vars['header_color'] = 'text-danger'
            status_vars['text_color'] = ''

        return status_vars

    def get_fleet(self):
        # Returns organisation fleet
        return self.aircraft_list.filter(operator=self, details_rev__isnull=False)

    @property
    def pytz_timezone(self):
        longitude = getattr(self, 'longitude')
        latitude = getattr(self, 'latitude')

        if longitude and latitude:
            tf = TimezoneFinder()
            tz = tf.timezone_at(lng=float(longitude),
                                lat=float(latitude))

            return pytz.timezone(tz)

    def get_operable_fleet(self):
        # Returns operable fleet for organisation and all departments
        qs = self.aircraft_list.model.objects

        parents_q = (
            Q(pk=self.pk) |
            Q(departments__organisation_id=self.pk) |
            Q(departments__organisation__departments__organisation_id=self.pk) |
            Q(departments__organisation__departments__organisation__departments__organisation_id=self.pk) |
            Q(details__department_of__departments__organisation_id=self.pk)
        )

        qs = qs.filter(
            operator__in=Organisation.objects.filter(parents_q),
            details_rev__isnull=False,
        )
        return qs


@receiver(post_save, sender=Organisation)
def organisation_post_save_tasks(sender, instance, **kwargs): # noqa
    from ..utils.tags import update_organisation_default_tags
    update_organisation_default_tags(instance)


class OrganisationDetails(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     null=True,
                                     on_delete=models.CASCADE,
                                     related_name='history')
    registered_name = models.CharField(_("Registered Name"), max_length=100)
    trading_name = models.CharField(_("Trading Name"), max_length=100,
                                    null=True, blank=True)
    country = models.ForeignKey("core.Country", verbose_name=_("Country"),
                                on_delete=models.RESTRICT)
    type = models.ForeignKey(OrganisationType, verbose_name=_("Type"),
                             on_delete=models.RESTRICT)
    tax_number = models.CharField(_("Tax Number"), max_length=100,
                                  null=True, blank=True)
    department_of = models.ForeignKey("organisation.Organisation",
                                      verbose_name=_("Department Of"),
                                      related_name='departments',
                                      null=True, blank=True,
                                      on_delete=models.CASCADE)
    is_trading = models.BooleanField(_("Is Trading?"), default=True)
    trading_ceased_date = models.DateField(_("Trading Ceased Date"),
                                           auto_now=False, auto_now_add=False,
                                           null=True, blank=True)
    change_effective_date = models.DateField(_("Change Effective Date"),
                                             auto_now=False, auto_now_add=False,
                                             default=datetime.now,
                                             )
    supplier_organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Billing Supplier"),
                                              null=True, blank=True,
                                              related_name='supplied_organisations',
                                              on_delete=models.SET_NULL)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   related_name='updated_organisation_details',
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=False, auto_now_add=True, null=True)

    class Meta:
        db_table = 'organisations_history'

    def __str__(self):
        return f'{self.registered_name}'

    @property
    def is_missing_details(self):
        type_attrs = {
            1: 'operator_details',
            3: 'handler_details',
            4: 'ipa_details',
            5: 'oilco_details',
            8: 'airport_details'
        }

        return self.type_id in type_attrs and not getattr(self.organisation, type_attrs[self.type_id], None)

    @property
    def operational_status(self):
        # TODO: Move to the Organisation model to optimize N+1 queries issue
        code = None
        text = None
        badge_bg = None
        text_color = None
        header_color = None

        if not self.is_trading:
            code = 'ceased_trading'
            text = 'Ceased Trading'
            badge_bg = 'bg-grey'
            text_color = 'organisation-ceased-trading'
            header_color = 'text-black-50'

        if self.organisation.is_sanctioned_ofac == True:
            sanctioned = True
        else:
            sanctioned = False

        if sanctioned:
            code = 'sanctioned'
            text = 'Sanctioned'
            badge_bg = 'bg-danger'
            header_color = 'text-danger'
            text_color = ''

        status_vars = {
            'code': code,
            'text': text or '',
            'text_color': text_color,
            'badge_bg': badge_bg,
            'header_color': header_color,
        }
        return status_vars

    @property
    def data_status(self):
        code = None
        text = None
        badge_bg = None
        text_color = None
        header_color = None

        code = 'missing details'
        text = 'Missing Details'
        badge_bg = 'bg-warning'
        header_color = 'text-danger'
        text_color = ''

        status_vars = {
            'missing_details': self.is_missing_details,
            'code': code,
            'text': text or '',
            'text_color': text_color,
            'badge_bg': badge_bg,
            'header_color': header_color,
        }
        return status_vars

    @property
    def registered_and_trading_name(self):
        if self.trading_name:
            return f'{self.registered_name} T/A {self.trading_name}'
        else:
            return self.registered_name


class OrganisationRestricted(models.Model):
    organisation = models.OneToOneField("organisation.Organisation",
                                        related_name='organisation_restricted',
                                        on_delete=models.CASCADE)
    is_customer = models.BooleanField(_("Customer?"), default=False)
    is_fuel_seller = models.BooleanField(_("Fuel Seller?"), default=False)
    is_service_supplier = models.BooleanField(_("Service Supplier?"), default=False)
    is_competitor = models.BooleanField(_("Competitor?"), default=False)
    is_invoiceable = models.BooleanField(_("Invoiceable?"), default=True)
    invoiceable_organisation = models.ForeignKey("organisation.Organisation",
                                                 null=True, blank=True,
                                                 on_delete=models.SET_NULL,
                                                 related_name='invoiceables')

    class Meta:
        db_table = 'organisations_restricted'

    def __str__(self):
        return f'{self.organisation}'


class OrganisationLogoMotto(models.Model):
    organisation = models.OneToOneField("organisation.Organisation", verbose_name=_("Organisation"),
                                        on_delete=models.CASCADE, related_name='logo_motto')
    logo = models.FileField(_("Logo"), storage=OrganisationsLogosStorage(), null=True, blank=True)
    motto = models.CharField(_("Motto"), max_length=255, null=True, blank=True)
    cascade_to_departments = models.BooleanField(_("Cascade Logo/Motto to Departments?"), default=False)

    class Meta:
        db_table = 'organisations_logos_mottos'

    def __str__(self):
        return f'{self.organisation}'


class OrganisationAddress(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Organisation"),
                                     related_name='addresses',
                                     on_delete=models.CASCADE)
    line_1 = models.CharField(_("Address Line 1"), max_length=100)
    line_2 = models.CharField(_("Address Line 2"), max_length=100, null=True, blank=True)
    line_3 = models.CharField(_("Address Line 3"), max_length=100, null=True, blank=True)
    town_city = models.CharField(_("Town / City"), max_length=100, null=True)
    state = models.CharField(_("State / County"), max_length=100, null=True, blank=True)
    post_zip_code = models.CharField(_("Post Zip Code"), max_length=50)
    country = models.ForeignKey("core.Country", verbose_name=_("Country"), on_delete=models.CASCADE)
    airport = models.ForeignKey("organisation.Organisation", verbose_name=_("Airport"),
                                null=True, blank=True,
                                limit_choices_to={'details__type_id': 8,
                                                  'airport_details__isnull': False},
                                related_name='airport_organisations_addresses',
                                on_delete=models.SET_NULL)
    email = models.EmailField(_("Email"), max_length=254, null=True, blank=True)
    phone = models.CharField(_("Phone"), max_length=128, null=True, blank=True,
                             validators=[phone_regex_validator])
    fax = models.CharField(_("Fax"), max_length=128, null=True, blank=True,
                           validators=[phone_regex_validator])
    is_primary_address = models.BooleanField(_("Primary Address?"), default=False)
    is_postal_address = models.BooleanField(_("Postal Address?"), default=False)
    is_physical_address = models.BooleanField(_("Physical Address?"), default=False)
    is_billing_address = models.BooleanField(_("Billing Address?"), default=True)

    class Meta:
        db_table = 'organisations_addresses'

    def __str__(self):
        return f'{self.pk}'


class OrganisationTag(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     on_delete=models.CASCADE)
    tag = models.ForeignKey("core.Tag", on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_tags'

    def __str__(self):
        return f'{self.tag}'


class TripSupportClient(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     on_delete=models.CASCADE)
    client = models.ForeignKey("organisation.Organisation",
                               limit_choices_to={'operator_details__isnull': False},
                               on_delete=models.CASCADE,
                               related_name='trip_support_companies')

    class Meta:
        db_table = 'organisations_trip_support_clients'

    def __str__(self):
        return f'{self.organisation}'


class OrganisationAircraftType(models.Model):
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Organisation"),
                                     related_name='organisation_aircrafts',
                                     on_delete=models.CASCADE)
    aircraft_type = models.ForeignKey("aircraft.AircraftType",
                                      verbose_name=_("Aircraft Type"),
                                      on_delete=models.CASCADE)
    mtow_override_kg = models.BigIntegerField(_("MTOW Override KG"), null=True, blank=True)
    mtow_override_lbs = models.BigIntegerField(_("MTOW Override LBS"), null=True, blank=True)

    class Meta:
        db_table = 'organisations_aircraft_types'

    def __str__(self):
        return f'{self.aircraft_type}'

    @property
    def mtow_override_kg_text(self):
        if self.mtow_override_kg:
            return f'{self.mtow_override_kg} kg'
        return 'TBC'

    @property
    def mtow_override_lbs_text(self):
        if self.mtow_override_lbs:
            return f'{self.mtow_override_lbs} lbs'
        return 'TBC'


class OrganisationPaymentMethod(models.Model):
    name = models.CharField(max_length = 100)
    is_credit = models.BooleanField(verbose_name=_('Credit?'))
    is_on_account = models.BooleanField(verbose_name=_('Account?'))
    is_cash = models.BooleanField(verbose_name=_('Cash?'))
    is_card = models.BooleanField(verbose_name=_('Card?'))

    class Meta:
        db_table = 'organisations_payment_methods'

    def __str__(self):
        return f'{self.name}'

    @property
    def methods_list(self):
        methods_list = []

        if self.is_cash:
            methods_list.append('Cash')
        if self.is_card:
            methods_list.append('Card')
        if self.is_credit:
            methods_list.append('Credit')
        if self.is_on_account:
            methods_list.append('Account')

        return ', '.join(methods_list)


class OrganisationAcceptedPaymentMethodQuerySet(models.QuerySet):
    def with_details(self):
        return self.annotate(
            methods_str=Concat(
                Case(When(Q(payment_method__is_credit=True), then=Value('Credit '))),
                Case(When(Q(payment_method__is_on_account=True), then=Value('Account '))),
                Case(When(Q(payment_method__is_cash=True), then=Value('Cash '))),
                Case(When(Q(payment_method__is_card=True), then=Value('Card '))),
            )
        )


class OrganisationAcceptedPaymentMethod(models.Model):
    organisation = models.ForeignKey(Organisation,
                                        verbose_name=_("Organisation"), on_delete=models.CASCADE,
                                        related_name='payment_methods')
    payment_method = models.OneToOneField(OrganisationPaymentMethod,
                                        verbose_name=_("Payment Method"), on_delete=models.CASCADE,
                                        related_name=('accepted_payment_method'))
    currency = models.ForeignKey("core.Currency",
                                        verbose_name=_("Currency"), null=True, on_delete=models.SET_NULL)

    objects = OrganisationAcceptedPaymentMethodQuerySet.as_manager()

    class Meta:
        db_table = 'organisations_accepted_payment_methods'

    def __str__(self):
        return f'{self.payment_method} ({self.currency})'


class OrganisationContactDetailsQuerySet(models.QuerySet):
    def with_details(self):
        return self.annotate(
            person=Case(
                When(Q(organisations_people__isnull=False), then=(Concat(
                    F('organisations_people__person__details__first_name'),
                    Value(' '),
                    F('organisations_people__person__details__last_name'),
                    Value(' ('),
                    F('organisations_people__job_title'),
                    Value(') '))
                )),
                default=Value('--'),
                output_field=CharField()
            ),
            locations_str=StringAgg(
                Concat(
                    F('locations__airport_details__icao_code'),
                    Value(' / '),
                    F('locations__airport_details__iata_code'),
                ),
                delimiter=', ',
                distinct=True,
                default=Value('--')
            ),
        )


class OrganisationContactDetails(models.Model):
    organisation = models.ForeignKey("Organisation", verbose_name=_("Organisation"),
                                     on_delete=models.CASCADE, related_name='organisation_contact_details')
    organisations_people = models.ForeignKey("OrganisationPeople", verbose_name=_("Person"),
                                             on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='organisation_contact_details')
    email_address = models.EmailField(_("Email Address"), max_length=250, null=True, blank=True)
    phone_number = models.CharField(_("Phone Number"), max_length=128, null=True, blank=True,
                                    validators=[phone_regex_validator])
    phone_number_use_for_whatsapp = models.BooleanField(_("Use for WhatsApp?"), default=False)
    phone_number_use_for_telegram = models.BooleanField(_("Use for Telegram?"), default=False)
    description = models.CharField(_("Description"), max_length=100)
    supplier_include_for_fuel_quotes = models.BooleanField(_("Include for Supplier Fuel Quotes?"), default=False)
    supplier_include_for_fuel_orders = models.BooleanField(_("Include for Supplier Fuel Orders?"), default=False)
    supplier_include_for_fuel_pricing_updates = models.BooleanField(_("Include for Supplier Fuel Pricing Updates?"),
                                                                    default=False)
    supplier_include_for_fuel_invoicing = models.BooleanField(_("Include for Supplier Fuel Invoicing?"), default=False)
    supplier_include_for_gh_quotes = models.BooleanField(_("Include for Supplier Handling Quotes?"), default=False)
    supplier_include_for_gh_orders = models.BooleanField(_("Include for Supplier Handling Orders?"), default=False)
    supplier_include_for_gh_invoicing = models.BooleanField(_("Include for Supplier Handling Invoicing?"),
                                                            default=False)
    supplier_include_for_credit_control = models.BooleanField(_("Include for Supplier Credit Control?"), default=False)
    client_include_for_quotes = models.BooleanField(_("Include for Client Quotes?"), default=False)
    client_include_for_orders = models.BooleanField(_("Include for Client Orders?"), default=False)
    client_include_for_invoicing = models.BooleanField(_("Include for Client Invoicing?"), default=False)
    client_include_for_marketing = models.BooleanField(_("Include for Client Marketing?"), default=False)
    client_include_for_credit_control = models.BooleanField(_("Include for Client Credit Control?"), default=False)
    address_to = models.BooleanField(_("TO"), default=False)
    address_cc = models.BooleanField(_("CC"), default=False)
    address_bcc = models.BooleanField(_("BCC"), default=False)
    comments = models.CharField(_("Comments"), max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True, auto_now_add=False)
    updated_by = models.ForeignKey("user.Person", verbose_name=_("Updated By"),
                                   null=True, on_delete=models.SET_NULL)

    locations = models.ManyToManyField("Organisation",
                                       verbose_name=_('Applicable Location(s)'),
                                       through='OrganisationContactDetailsLocation',
                                       related_name='contact_details_for_location',
                                       blank=True, limit_choices_to={'details__type_id': 8,
                                                                     'airport_details__isnull': False})

    COMMS_CLIENT_CHOICES = {
        'CQ': ('client_include_for_quotes', 'Quotes'),
        'CO': ('client_include_for_orders', 'Orders'),
        'CI': ('client_include_for_invoicing', 'Invoicing'),
        'CM': ('client_include_for_marketing', 'Marketing'),
        'CCC': ('client_include_for_credit_control', 'Credit Control'),
    }

    COMMS_SUPPLIER_CHOICES = {
        'SFQ': ('supplier_include_for_fuel_quotes', 'Fuel Quotes'),
        'SFO': ('supplier_include_for_fuel_orders', 'Fuel Orders'),
        'SFU': ('supplier_include_for_fuel_pricing_updates', 'Fuel Pricing Updates'),
        'SFI': ('supplier_include_for_fuel_invoicing', 'Fuel Invoicing'),
        'SHQ': ('supplier_include_for_gh_quotes', 'Ground Handling Quotes'),
        'SHO': ('supplier_include_for_gh_orders', 'Ground Handling Orders'),
        'SHI': ('supplier_include_for_gh_invoicing', 'Ground Handling Invoicing'),
        'SCC': ('supplier_include_for_credit_control', 'Credit Control'),
    }

    objects = OrganisationContactDetailsQuerySet.as_manager()

    class Meta:
        db_table = 'organisations_contact_details'

    @property
    def comms_settings_client(self):
        return [k for k, (field_name, _) in OrganisationContactDetails.COMMS_CLIENT_CHOICES.items()
                if getattr(self, field_name, False)]

    @comms_settings_client.setter
    def comms_settings_client(self, value):
        for code in self.COMMS_CLIENT_CHOICES:
            if code in value:
                setattr(self, self.COMMS_CLIENT_CHOICES[code][0], True)
            else:
                setattr(self, self.COMMS_CLIENT_CHOICES[code][0], False)

    @property
    def comms_settings_supplier(self):
        return [k for k, (field_name, _) in OrganisationContactDetails.COMMS_SUPPLIER_CHOICES.items()
                if getattr(self, field_name, False)]

    @comms_settings_supplier.setter
    def comms_settings_supplier(self, value):
        for code in self.COMMS_SUPPLIER_CHOICES:
            if code in value:
                setattr(self, self.COMMS_SUPPLIER_CHOICES[code][0], True)
            else:
                setattr(self, self.COMMS_SUPPLIER_CHOICES[code][0], False)

    @property
    def email_fields_icon_str(self):
        icon_str = ''

        if self.address_to:
            email_field = 'TO:'
        elif self.address_cc:
            email_field = 'CC:'
        elif self.address_bcc:
            email_field = 'BCC:'
        else:
            return icon_str

        icon_str += get_datatable_badge(
            badge_text=email_field,
            badge_class='bg-gray-400 badge-multiline badge-250 pt-1',
            tooltip_text=f"Use email in '{email_field}' field",
            tooltip_placement='top'
        )

        return icon_str

    @property
    def included_in_choices_str(self):
        icon_str = ''

        for code, (field_name, long_repr) in (self.COMMS_SUPPLIER_CHOICES | self.COMMS_CLIENT_CHOICES).items():
            if getattr(self, field_name, False):
                icon_str += get_colored_circle(
                    color='white',
                    text=code,
                    tooltip_text=f"{'Client' if code.startswith('C') else 'Supplier'} {long_repr}",
                    tooltip_placement='top',
                    additional_classes='large me-1 mb-1'
                )

        return f'<div class="d-flex flex-wrap">{icon_str}</div>'

    @property
    def location_badges_str(self):
        badge_str = ''
        locations = self.locations.all()

        if not locations:
            return

        for location in locations:
            badge_str += get_datatable_badge(
                badge_text=location.airport_details.icao_iata,
                badge_class='bg-info datatable-badge-normal badge-multiline badge-250',
                tooltip_enable_html=True
            )

        return f'<div class="d-flex flex-wrap">{badge_str}</div>'

    @property
    def phone_number_icons_str(self):
        badge_str = ''

        if self.phone_number_use_for_whatsapp:
            badge_str += get_fontawesome_icon(
                icon_name='whatsapp',
                tooltip_text='Use phone number for WhatsApp',
                tooltip_placement='top',
                fontawesome_family_class='fab',
                additional_classes='medium-font'
            )

        if self.phone_number_use_for_telegram:
            badge_str += get_fontawesome_icon(
                icon_name='telegram',
                tooltip_text='Use phone number for Telegram',
                tooltip_placement='top',
                fontawesome_family_class='fab',
                additional_classes='medium-font'
            )

        return f'<span class="nowrap">{badge_str}</span>'

    @property
    def repr_for_additional_emails_list(self):
        prefix = ''

        if self.address_to:
            prefix = 'TO:'
        elif self.address_cc:
            prefix = 'CC:'
        elif self.address_bcc:
            prefix = 'BCC:'

        return f'{prefix}{self.email_address} ({self.description})'

    @property
    def repr_for_recipients_list(self):
        return (f'{self.organisations_people.person.fullname}'
                f' <i class="text-gray-400">({self.organisations_people.job_title})</i>'
                f'<br>{self.email_fields_icon_str}{self.email_address}')


class OrganisationContactDetailsLocation(models.Model):
    organisations_contact_details = models.ForeignKey("OrganisationContactDetails",
                                                      verbose_name=_("Contact Details"),
                                                      on_delete=models.CASCADE)
    location = models.ForeignKey("Organisation", verbose_name=_("Location"),
                                 on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_contact_details_locations'
