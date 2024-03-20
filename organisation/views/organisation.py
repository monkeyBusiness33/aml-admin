import json
import re
from datetime import date

from ajax_datatable.views import AjaxDatatableView
from django.db.models import ExpressionWrapper, Q, BooleanField
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from bootstrap_modal_forms.generic import BSModalReadView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_organisation_status_badge, \
    get_datatable_missing_details_status_badge
from dla_scraper.utils.scraper import reconcile_org_name
from organisation.forms import OrganisationAddressFormSet, OrganisationDetailsForm, OrganisationLogoMottoForm, \
    OrganisationRestictedForm, OrganisationTypesSelectForm
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OrganisationDetails, OrganisationLogoMotto, OrganisationRestricted, \
    OrganisationType
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin


class OrganisationsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']
    initial_order = [["registered_name", "asc"], ]
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    render_row_details_template_name = 'render_row_details.html'

    def get_filter_param(self, key):
        try:
            value = json.loads(self.request.POST.get('checkbox_filter_data'))[key]
        except:
            value = None
        return value

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.filter(details__department_of__isnull=True)

        if self.get_filter_param('only_missing_details'):
            qs = qs.annotate(missing_details=ExpressionWrapper(
                Q(details__type_id=1) & Q(operator_details__isnull=True) |
                Q(details__type_id=3) & Q(handler_details__isnull=True) |
                Q(details__type_id=4) & Q(ipa_details__isnull=True) |
                Q(details__type_id=5) & Q(oilco_details__isnull=True) |
                Q(details__type_id=8) & Q(airport_details__isnull=True),
                output_field=BooleanField()))

            qs = qs.annotate(missing_details_deps=ExpressionWrapper(
                Q(departments__organisation__details__type_id=1) & Q(departments__organisation__operator_details__isnull=True) |
                Q(departments__organisation__details__type_id=3) & Q(departments__organisation__handler_details__isnull=True) |
                Q(departments__organisation__details__type_id=4) & Q(departments__organisation__ipa_details__isnull=True) |
                Q(departments__organisation__details__type_id=5) & Q(departments__organisation__oilco_details__isnull=True) |
                Q(departments__organisation__details__type_id=8) & Q(departments__organisation__airport_details__isnull=True),
                output_field=BooleanField()))

            qs = qs.annotate(missing_details_deps_of_deps=ExpressionWrapper(
                Q(departments__organisation__departments__organisation__details__type_id=1) & Q(departments__organisation__departments__organisation__operator_details__isnull=True) |
                Q(departments__organisation__departments__organisation__details__type_id=3) & Q(departments__organisation__departments__organisation__handler_details__isnull=True) |
                Q(departments__organisation__departments__organisation__details__type_id=4) & Q(departments__organisation__departments__organisation__ipa_details__isnull=True) |
                Q(departments__organisation__departments__organisation__details__type_id=5) & Q(departments__organisation__departments__organisation__oilco_details__isnull=True) |
                Q(departments__organisation__departments__organisation__details__type_id=8) & Q(departments__organisation__departments__organisation__airport_details__isnull=True),
                output_field=BooleanField()))

            qs = qs.filter(Q(missing_details=True) |
                           Q(missing_details_deps=True) |
                           Q(missing_details_deps_of_deps=True))

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name parent-row', 'width': '320px'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name',
         'visible': True, 'width': '320px'},
        {'name': 'type', 'title': 'Organisation Type', 'foreign_field': 'details__type__name', 'visible': True,
         'width': '250px'},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, 'width': '200px'},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def _filter_queryset(self, column_names, search_value, qs, global_filtering):
        from ajax_datatable.app_settings import TEST_FILTERS
        from ajax_datatable.views import build_column_filter
        from inspect import trace

        if TEST_FILTERS:
            trace(
                ', '.join(column_names),
                prompt='%s filtering "%s" over fields' % ('Global' if global_filtering else 'Column', search_value)
            )

        search_filters = Q()
        for column_name in column_names:

            column_obj = self.column_obj(column_name)
            column_spec = self.column_spec_by_name(column_name)

            # v4.0.2: we now accept multiple search values (to be ORed)
            # Split search values;
            # example: 'aaa + bbb' -> ['aaa ', ' bbb']
            if self.search_values_separator and self.search_values_separator in search_value:
                search_value = [t.strip() for t in search_value.split(self.search_values_separator)]

            column_filter = build_column_filter(column_name, column_obj, column_spec, search_value, global_filtering)
            if column_filter:
                search_filters |= column_filter
                if TEST_FILTERS:
                    try:
                        qstest = qs.filter(column_filter)
                        trace('%8d/%8d records filtered over column "%s"' % (qstest.count(), qs.count(), column_name, ))
                    except Exception as e:
                        trace('ERROR filtering over column "%s": %s' % (column_name, str(e)))

        if TEST_FILTERS:
            trace(search_filters)

        if 'registered_name' in column_names:
            return qs.filter(search_filters |
                             Q(departments__registered_name__icontains=search_value) |
                             Q(departments__organisation__departments__registered_name__icontains=search_value)
                             ).distinct()
        elif 'trading_name' in column_names:
            return qs.filter(search_filters |
                             Q(departments__trading_name__icontains=search_value) |
                             Q(departments__organisation__departments__trading_name__icontains=search_value)
                             ).distinct()
        else:
            return qs.filter(search_filters)

    def sort_queryset(self, params, qs):
        # Ensure that the results are distinct
        if self.get_filter_param('only_missing_details'):
            orders = [o.column_link.get_field_search_path() for o in params['orders']]
            qs = qs.distinct(*orders, 'pk')

        return super().sort_queryset(params, qs)

    def customize_row(self, row, obj):
        departments = obj.departments.exists()
        if departments:
            departments_class = 'has_children'
        else:
            departments_class = ''

        row['registered_name'] = f'<span data-url="' \
                                 f'{obj.get_absolute_edit_url() if obj.details.data_status["missing_details"] else obj.get_absolute_url()}' \
                                 f'" class="{departments_class}"\>{obj.details.registered_name}</span>'
        row['status'] = ''.join(filter(None,
                                       (get_datatable_organisation_status_badge(obj.operational_status),
                                        get_datatable_missing_details_status_badge(obj.details.data_status))))

        return


class OrganisationsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Organisation',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:organisation_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        header_checkbox_list = [
            {
                'checkbox_text': 'Only Show Org. with Missing Details',
                'checkbox_name': 'only_missing_details',
                'checkbox_value': True,
                'checkbox_perm': True,
            }
        ]

        metacontext = {
            'title': 'Organisations',
            'page_id': 'organisations_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:organisations_ajax',
            'header_checkbox_list': json.dumps(header_checkbox_list),
            'header_buttons_list': json.dumps(header_buttons_list),
        }

        context['metacontext'] = metacontext
        return context


class OrganisationChildsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']
    render_row_details_template_name = 'render_row_details.html'

    def get_filter_param(self, key):
        try:
            value = json.loads(self.request.POST.get('checkbox_filter_data'))[key]
        except:
            value = None
        return value

    def get_initial_queryset(self, request=None):
        qs = Organisation.objects.filter(details__department_of_id=self.kwargs['pk'])

        if self.get_filter_param('only_missing_details'):
            qs = qs.annotate(missing_details=ExpressionWrapper(
                Q(details__type_id=1) & Q(operator_details__isnull=True) |
                Q(details__type_id=3) & Q(handler_details__isnull=True) |
                Q(details__type_id=4) & Q(ipa_details__isnull=True) |
                Q(details__type_id=5) & Q(oilco_details__isnull=True) |
                Q(details__type_id=8) & Q(airport_details__isnull=True),
                output_field=BooleanField()))

            qs = qs.annotate(missing_details_deps=ExpressionWrapper(
                Q(departments__organisation__details__type_id=1) & Q(departments__organisation__operator_details__isnull=True) |
                Q(departments__organisation__details__type_id=3) & Q(departments__organisation__handler_details__isnull=True) |
                Q(departments__organisation__details__type_id=4) & Q(departments__organisation__ipa_details__isnull=True) |
                Q(departments__organisation__details__type_id=5) & Q(departments__organisation__oilco_details__isnull=True) |
                Q(departments__organisation__details__type_id=8) & Q(departments__organisation__airport_details__isnull=True),
                output_field=BooleanField()))

            qs = qs.filter(Q(missing_details=True) |
                           Q(missing_details_deps=True))

        return qs

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name', 'width': '320px'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name',
         'visible': True, 'width': '320px'},
        {'name': 'type', 'title': 'Organisation Type', 'foreign_field': 'details__type__name',
         'visible': True, 'width': '250px'},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, 'width': '200px'},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def sort_queryset(self, params, qs):
        # Ensure that the results are distinct
        if self.get_filter_param('only_missing_details'):
            orders = [o.column_link.get_field_search_path() for o in params['orders']]
            qs = qs.distinct(*orders, 'pk')

        return super().sort_queryset(params, qs)

    def customize_row(self, row, obj):
        departments = obj.departments.exists()
        if departments:
            departments_class = 'deps'
        else:
            departments_class = ''

        row['registered_name'] = f'<span data-url="' \
                                 f'{obj.get_absolute_edit_url() if obj.details.data_status["missing_details"] else obj.get_absolute_url()}' \
                                 f'" class="{departments_class}"\>{obj.details.registered_name}</span>'
        row['status'] = ''.join(filter(None,
                                       (get_datatable_organisation_status_badge(obj.operational_status),
                                        get_datatable_missing_details_status_badge(obj.details.data_status))))

        return


class OrganisationDepartmentsAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.filter(details__department_of_id=self.kwargs['organisation_id'])

    column_defs = [
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name', 'width': '345px'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name',
         'visible': True, 'width': '340px'},
        {'name': 'type', 'title': 'Organisation Type', 'foreign_field': 'details__type__name',
         'visible': True, 'width': '250px'},
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name', 'visible': True,
         'choices': True, 'autofilter': True, 'width': '200px'},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        departments = obj.departments.exists()
        if departments:
            departments_class = 'deps'
        else:
            departments_class = ''

        if obj.details.data_status["missing_details"] and self.request.user.has_perm('core.p_contacts_update'):
            data_url = obj.get_absolute_edit_url()
        elif self.request.user.has_perm('core.p_contacts_view'):
            data_url = obj.get_absolute_url()
        else:
            data_url = ''
        row['registered_name'] = (f'<span data-url="{data_url}" class="{departments_class}">'
                                  f'{obj.details.registered_name}</span>')
        row['status'] = ''.join(filter(None,
                                       (get_datatable_organisation_status_badge(obj.operational_status),
                                        get_datatable_missing_details_status_badge(obj.details.data_status))))

        return


class OrganisationDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']


class OrganisationCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    """
    This view now covers the creation and edition of general org. details (organisations_history, addresses etc.)
    for all organisation types. During creation, the specific types can be selected in a form section on this page,
    with the main type being fixed and disabled if a button on type-specific list page was used.
    """
    template_name = 'organisation_create_edit.html'
    permission_required = ['core.p_contacts_create']
    context = None
    page_org_type = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.context = 'Edit' if self.organisation_id else 'Create'

        # Check if the creation is from type-spec. page and update form accordingly
        org_type_name_match = re.search(r'organisations?/(\w+)/create/', request.path)

        if org_type_name_match:
            org_types_dict = {
                'aircraft_operators': 1,
                'fuel_reseller': 2,
                'ground_handler': 3,
                'ipa': 4,
                'nasdl': 1002,
                'oilco': 5,
                'service_provider': 14,
                'trip_support_company': 11,
            }
            self.page_org_type = org_types_dict[org_type_name_match.groups()[0]]

    def get(self, request, *args, **kwargs):
        if self.organisation_id:
            organisation = Organisation.objects.get(pk=self.organisation_id)
        else:
            organisation = Organisation()

        if hasattr(organisation, 'details'):
            organisation_details = organisation.details
        else:
            organisation_details = OrganisationDetails()
            organisation_details.type_id = getattr(self, 'page_org_type', None)

        if hasattr(organisation, 'organisation_restricted'):
            organisation_restricted = organisation.organisation_restricted
        else:
            organisation_restricted = OrganisationRestricted()

        organisation_logo_motto = getattr(organisation, 'logo_motto', OrganisationLogoMotto())

        return self.render_to_response({
            'organisation': organisation,
            'context': self.context,
            'organisation_details_form': OrganisationDetailsForm(
                instance=organisation_details,
                prefix='organisation_details_form_pre',
                context=self.context, page_org_type=self.page_org_type),

            'organisation_restricted_form': OrganisationRestictedForm(
                instance=organisation_restricted,
                prefix='organisation_restricted_form_pre', ),

            'organisation_logo_motto_form': OrganisationLogoMottoForm(
                instance=organisation_logo_motto,
                prefix='organisation_logo_motto_form_pre',),

            'organisation_address_formset': OrganisationAddressFormSet(
                organisation=organisation,
                prefix='organisation_address_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        if self.organisation_id:
            organisation = Organisation.objects.get(pk=self.organisation_id)

            # Get a copy of existing details
            organisation_details = organisation.details
            organisation_details.pk = None
            organisation_details.updated_by = getattr(self, 'person')
            organisation_details.change_effective_date = date.today()
        else:
            organisation = None
            organisation_details = OrganisationDetails()
            organisation_details.updated_by = getattr(self, 'person')
            organisation_details.type_id = getattr(self, 'page_org_type', None)

        if hasattr(organisation, 'organisation_restricted'):
            organisation_restricted = organisation.organisation_restricted
        else:
            organisation_restricted = OrganisationRestricted()

        # TODO: Move instances initialization from get() method to setup(), to make instances available widely
        organisation_logo_motto = getattr(organisation, 'logo_motto', OrganisationLogoMotto())

        organisation_details_form = OrganisationDetailsForm(request.POST or None,
                                                            instance=organisation_details,
                                                            prefix='organisation_details_form_pre',
                                                            context=self.context, page_org_type=self.page_org_type)

        organisation_restricted_form = OrganisationRestictedForm(request.POST or None,
                                                                 instance=organisation_restricted,
                                                                 prefix='organisation_restricted_form_pre')

        organisation_logo_motto_form = OrganisationLogoMottoForm(request.POST or None, request.FILES or None,
                                                                 instance=organisation_logo_motto,
                                                                 prefix='organisation_logo_motto_form_pre')

        organisation_address_formset = OrganisationAddressFormSet(request.POST or None,
                                                                  organisation=organisation,
                                                                  prefix='organisation_address_formset_pre')

        # Process only if ALL forms are valid
        if all([
            organisation_details_form.is_valid(),
            organisation_restricted_form.is_valid(),
            organisation_logo_motto_form.is_valid(),
            organisation_address_formset.is_valid()
        ]):
            # Save Organisation details
            organisation_details = organisation_details_form.save()

            if self.organisation_id:
                organisation = Organisation.objects.get(pk=self.organisation_id)
                organisation.details = organisation_details
                organisation.save()
            else:
                organisation = Organisation.objects.create(
                    details=organisation_details,
                )

                # Store pending types in session, to control the redirection chain
                # For NASDLs, ignore any additional types (just in case front-end validation is not enough)
                request.session[f'pending_types-{organisation.pk}'] \
                    = [organisation_details.type.pk] \
                      + ([org_type.pk for org_type in organisation_details_form.cleaned_data['secondary_types']]
                         if organisation_details.type.pk != 1002 else [])

            organisation_details.organisation = organisation
            organisation_details.save()

            organisation_restricted = organisation_restricted_form.save(commit=False)
            organisation_restricted.organisation = organisation
            organisation_restricted.save()

            organisation_logo_motto = organisation_logo_motto_form.save(commit=False)
            organisation_logo_motto.organisation = organisation
            organisation_logo_motto.save()

            # Save Organisation addresses
            instances = organisation_address_formset.save(commit=False)
            for instance in instances:
                instance.organisation = organisation
            organisation_address_formset.save()

            # Trigger organisation post_save signal to assign tags regarding created details tables
            from django.db.models.signals import post_save
            post_save.send(Organisation, instance=organisation)

            # If organisation creation triggered from DLA scraper page, reconcile organisation as DLA supplier
            if request.GET.get('dla_name_id', None):
                reconcile_org_name(organisation, request.GET['dla_name_id'])

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'context': self.context,
                'organisation_details_form': organisation_details_form,
                'organisation_restricted_form': organisation_restricted_form,
                'organisation_logo_motto_form': organisation_logo_motto_form,
                'organisation_address_formset': organisation_address_formset,
            })


class OrganisationAddTypeView(AdminPermissionsMixin, BSModalReadView):
    template_name = 'organisations_pages_includes/_organisation_add_type_choice_modal.html'
    form_class = ConfirmationForm
    model = Organisation
    permission_required = ['core.p_contacts_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Create a list of btns for all the types that have details tables/forms, that the org doesn't already have
        modal_btn_list = [{'url': v, 'label': k} for k, v in self.object.missing_org_type_urls.items() if v]

        metacontext = {
            'title': 'Choose organisation type to add',
            'icon': 'fa-plus',
            'organisation': self.object
        }

        context['modal_btn_list'] = modal_btn_list
        context['metacontext'] = metacontext
        return context

