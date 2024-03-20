from ajax_datatable.views import AjaxDatatableView
from django.views.generic import TemplateView, DetailView

from core.utils.datatables_functions import get_datatable_dao_countries_badges
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, DaoCountry
from user.mixins import AdminPermissionsMixin


class DaoListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.dao()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'responsible_countries', 'title': 'Responsible Countries', 'visible': True, 'placeholder': True,
         'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['responsible_countries'] = get_datatable_dao_countries_badges(obj)
        return


class DaoListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Defense Attache Offices',
            'page_id': 'dao_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:daos_ajax',
        }

        context['metacontext'] = metacontext
        return context


class DaoDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.dao()


class DaoCountriesListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = DaoCountry
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        qs = DaoCountry.objects.filter(
            organisation_id=self.kwargs['dao_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': True, 'orderable': False, 'width': '10px'},
        {'name': 'responsible_country', 'title': 'Responsible Country', 'foreign_field':
            'responsible_country__name', 'visible': True},
        {'name': 'country_code', 'title': 'Code', 'foreign_field': 'responsible_country__code', 'visible': True},
    ]
