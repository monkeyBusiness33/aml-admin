from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalFormView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, FormView
from dla_scraper.tasks import run_dla_scraper_task
from organisation.models import Organisation
from user.mixins import AdminPermissionsMixin
from .forms import DLAReconcileNameForm, DLAPendingOrganisationUpdateForm, DLAScraperForm, DLASelectOrgTypeForm
from .models import DLASupplierName, DLAScraperPendingOrganisationUpdate, DLAContract, DLAScraperRun
from .utils.scraper import reconcile_org_name

import difflib


class DLAContractsView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['administration.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'DLA Fuel Contracts',
            'page_id': 'dla_contract_list',
            'datatable_uri': 'admin:dla_contracts_ajax',
        }

        context['metacontext'] = metacontext

        return context


class DLAScraperView(AdminPermissionsMixin, TemplateView):
    template_name = 'scraper_log.html'
    permission_required = ['administration.p_view']

    def suggest_org_for_name(self, name, name_list):
        suggested_name = difflib.get_close_matches(name.lower(), name_list, n=1, cutoff=0.7)

        if suggested_name:
            org = Organisation.objects.filter(details__registered_name__icontains=suggested_name[0])

            if org:
                return org.first().pk

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Scraper Log',
            'page_id': 'scraper_log',
            'button_id': 'scraper_run_btn',
            'button_text': 'Scrape',
            'button_url': 'admin:dla_scraper_run',
            'button_perm': 'administration.p_dla_contract_scrapper',
            'name_accept_button_text': 'Accept',
            'name_create_button_text': 'Create',
            'name_accept_button_icon': 'fa-check',
            'name_create_button_icon': 'fa-plus',
            'name_button_class': 'name-btn',
            'name_accept_button_class': 'name-accept-btn',
            'name_create_button_class': 'name-create-btn',
            'name_create_button_url': reverse_lazy('admin:dla_name_create'),
            'name_button_perm': 'administration.p_dla_contract_scrapper',
            'datatable_uri': 'admin:dla_scraper_log_ajax',
            'card_css_class': 'dla_name_card',
            'update_accept_button_text': 'Accept',
            'update_ignore_button_text': 'Ignore',
            'update_accept_button_icon': 'fa-check',
            'update_ignore_button_icon': 'fa-times',
            'update_accept_button_class': 'update-accept-btn',
            'update_ignore_button_class': 'update-ignore-btn',
            'update_button_perm': 'administration.p_dla_contract_scrapper',
            'update_card_css_class': 'pending_update_card',
            'scraper_start_msg': 'A scraper run was triggered. Come back to check the results in about 15 minutes.'
        }

        context['metacontext'] = metacontext

        # Create cards for new names that need to be reconciled
        names_to_reconcile = DLASupplierName.objects.filter(supplier_id=None).all()[:5]

        if names_to_reconcile:
            org_name_list = [name.lower()
                             for name
                             in Organisation.objects.values_list('details__registered_name', flat=True)]

        name_forms = [DLAReconcileNameForm(
            instance=name,
            # initial={'supplier': self.suggest_org_for_name(name.name, org_name_list)}
        ) for name in names_to_reconcile]

        context['name_forms'] = name_forms

        # Create cards for pending updates
        pending_organisation_updates = DLAScraperPendingOrganisationUpdate.objects.filter(
            ignored=False, applied=False).all()[:5]

        pending_update_forms = [DLAPendingOrganisationUpdateForm(
            instance=update,
        ) for update in pending_organisation_updates]

        context['pending_update_forms'] = pending_update_forms

        return context


class DLAScraperAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    http_method_names = ['post']
    model = DLAContract
    search_values_separator = '+'
    permission_required = ['administration.p_view']
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    render_row_details_template_name = 'render_row_details.html'

    def get_initial_queryset(self, request=None):
        return DLAContract.objects.all()

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'contract_reference', 'title': 'Contract Ref.', 'visible': True, 'width': '170px'},
        {'name': 'start_date', 'title': 'Start Date', 'visible': True, 'searchable': False, 'width': '130px'},
        {'name': 'end_date', 'title': 'End Date', 'visible': True, 'searchable': False, 'width': '130px'},
        {'name': 'early_termination_date', 'title': 'Early Termination Date', 'visible': True, 'searchable': False,
         'width': '130px'},
        {'name': 'is_active', 'title': 'Active', 'visible': True, 'searchable': False, 'width': '50px'},
        {'name': 'location', 'title': 'Location', 'foreign_field': 'location__airport_details__icao_code',
         'visible': True,
         'width': '250px'},
        {'name': 'location_iata', 'title': 'Location IATA', 'foreign_field': 'location__airport_details__iata_code',
         'visible': False, 'width': '0px'},
        {'name': 'supplier', 'title': 'Supplier', 'foreign_field': 'supplier__details__registered_name',
         'visible': True, 'width': '250px'},
        {'name': 'ipa', 'title': 'IPA', 'foreign_field': 'ipa__details__registered_name', 'visible': True,
         'width': '250px'},
    ]

    def filter_queryset(self, params, qs):
        qs = self.filter_queryset_by_date_range(params.get('date_from', None), params.get('date_to', None), qs)

        if 'search_value' in params:
            qs = self.filter_queryset_all_columns(params['search_value'], qs)

        for column_link in params['column_links']:
            if column_link.searchable and column_link.search_value:
                if column_link.name == 'location':
                    qs_icao = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)
                    qs = qs_icao.union(self.filter_queryset_by_column('location_iata', column_link.search_value, qs))
                else:
                    qs = self.filter_queryset_by_column(column_link.name, column_link.search_value, qs)

        return qs

    def customize_row(self, row, obj):
        row['start_date'] = obj.start_date.strftime("%Y-%m-%d")
        row['end_date'] = obj.end_date.strftime("%Y-%m-%d")
        row['location'] = f'{obj.location.airport_details.icao_code}' + \
                          (f' / {obj.location.airport_details.iata_code}' if obj.location.airport_details.iata_code else '')
        row['supplier'] = 'UNRECONCILED' if not row['supplier'] else row['supplier']

        if obj.early_termination_date:
            row['early_termination_date'] = obj.early_termination_date.strftime("%Y-%m-%d")
        return


class DLAScraperLogAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    http_method_names = ['post']
    model = DLAScraperRun
    search_values_separator = '+'
    permission_required = ['administration.p_view']
    initial_order = [["run_at", "desc"], ]
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    render_row_details_template_name = 'render_row_details.html'

    def get_initial_queryset(self, request=None):
        return DLAScraperRun.objects.all()

    column_defs = [
        AjaxDatatableView.render_row_tools_column_def(),
        {'name': 'id', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'run_at', 'title': 'Run At', 'visible': True, 'searchable': False, 'width': '120px', 'orderable': True},
        {'name': 'status', 'title': 'Status', 'className': 'scraper-log-row-status', 'visible': True, 'searchable': True,
         'foreign_field': 'status__id', 'width': '50px'},
        {'name': 'log', 'title': 'Event Log', 'visible': True, 'searchable': True, 'width': '450px'},
    ]

    def customize_row(self, row, obj):
        row['run_at'] = obj.run_at.strftime("%Y-%m-%d %H:%M %Z")
        log = obj.log
        msg = ''

        row['status'] = obj.status.code
        if row['status'] == 'ERROR' and 'exception_type' in log:
            exception_msg = ''

            if log['exception_type'] == 'Exception' and 'exception_msg' in log:
                exception_msg = f" ({log['exception_msg']}) "

            msg = f"<p>An exception of type <b>{log['exception_type']}{exception_msg}</b> occurred during data scraping.<p>"
        elif row['status'] == 'WARNING':
            if 'new_contracts' in log:
                new_contracts = log['new_contracts']
                msg += f"<p><b>The following new contracts have been added:<ul>{',<br>'.join(new_contracts)}</ul></b></p>"

            if 'changed_contracts' in log:
                changed_contracts = log['changed_contracts']
                con_strings = []

                for con in changed_contracts:
                    con_str = '<b>' + list(con.keys())[0] + '</b>:<ul>'

                    for val in con.values():
                        for prop in val.keys():
                            if prop == 'ipa':
                                con_str += f'<b>{prop}</b>: from <b>' \
                                           f'{Organisation.objects.get(pk=val[prop][0]).details.registered_name if val[prop][0] != "None" else "None"}' \
                                           f'</b> to <b>' \
                                           f'{Organisation.objects.get(pk=val[prop][1]).details.registered_name if val[prop][1] != "None" else "None"}' \
                                           f'</b><br>'
                            else:
                                con_str += f'<b>{prop}</b>: from <b>{val[prop][0]}</b> to <b>{val[prop][1]}</b><br>'

                    con_strings.append(con_str + '</ul>')

                msg += f"<p><b>The following contracts have changed:</b><ul>{'<br>'.join(con_strings)}</ul></p>"

            if 'removed_contracts' in log:
                removed_contracts = log['removed_contracts']
                msg += f"<p><b>The following contracts have been removed:<ul>{',<br>'.join(removed_contracts)}</ul></b></p>"

            if 'new_vendor_names' in log:
                vendor_names = log['new_vendor_names']
                msg += f"<p>{len(vendor_names)} new vendor name{'s' if len(vendor_names) > 1 else ''} found: <b>{', '.join(vendor_names)}</b>.<br></p>"

            if 'missing_dates' in log:
                missing_dates = log['missing_dates']
                msg += f"<p>The following contracts are <b>missing dates</b> in the source data: <b>{', '.join(missing_dates)}</b>.<br></p>"

            if 'missing_location' in log:
                missing_location = log['missing_location']
                msg += f"<p>The <b>location</b> for the following contracts could not be reconciled:  <b>{', '.join(missing_location)}</b>.<br></p>"

            if 'missing_supplier' in log:
                missing_supplier = log['missing_supplier']
                msg += f"<p>The <b>supplier</b> for the following contracts could not be reconciled: <b>{', '.join(missing_supplier)}</b>.<br></p>"

            if 'missing_ipa' in log:
                missing_ipa = log['missing_ipa']
                msg += f"<p>The <b>IPA</b> for the following contracts could not be reconciled: <b>{', '.join(missing_ipa)}</b>.<br></p>"

        row['log'] = msg if msg else '<p>No changes found.</p>'

        return


class DLAScraperRunAjaxView(AdminPermissionsMixin, SuccessMessageMixin, FormView):
    http_method_names = ['post']
    permission_required = ['administration.p_dla_contract_scrapper']
    form_class = DLAScraperForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        return kwargs

    def form_valid(self, form, *args, **kwargs):
        run_dla_scraper_task.delay(scheduled=False)

        return JsonResponse({
            'status': True
        }, status=200)


class DLAReconcileNameAjaxView(AdminPermissionsMixin, FormView):
    http_method_names = ['post']
    permission_required = ['administration.p_dla_contract_scrapper']
    form_class = DLAReconcileNameForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        return kwargs

    def form_invalid(self, form, *args, **kwargs):
        return JsonResponse({
            "errors": form.errors,
        }, status=422)

    def form_valid(self, form, *args, **kwargs):
        form_data = form.cleaned_data

        supplier = Organisation.objects.filter(pk=form_data['supplier'].pk).first()
        reconcile_org_name(supplier, form_data['id'])

        return JsonResponse({
            "status": True,
        }, status=200)


class DLASelectOrgTypeView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'org_type_select.html'
    form_class = DLASelectOrgTypeForm
    permission_required = ['administration.p_dla_contract_scrapper']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        kwargs['dla_name_id'] = self.request.GET['dla_name_id']

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Select Type of Organisation to Create',
            'modal_id': 'org_type_select_modal',
            'icon': 'fa-cogs',
            'action_button_text': 'Create',
        }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form, *args, **kwargs):
        form_data = form.cleaned_data
        org_type_id = form_data['type']

        success_urls = {
            '1': 'admin:aircraft_operators_create',
            '2': 'admin:fuel_reseller_create',
            '3': 'admin:ground_handler_create',
            '4': 'admin:ipa_create',
            '5': 'admin:oilco_create',
        }

        return HttpResponseRedirect(reverse(success_urls[org_type_id]) + f'?dla_name_id={form_data["dla_name_id"]}')


class DLAPendingUpdateAcceptAjaxView(AdminPermissionsMixin, FormView):
    http_method_names = ['post']
    permission_required = ['administration.p_dla_contract_scrapper']
    form_class = DLAPendingOrganisationUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        return kwargs

    def form_invalid(self, form, *args, **kwargs):
        return JsonResponse({
            "errors": form.errors,
        }, status=422)

    def form_valid(self, form, *args, **kwargs):
        form_data = form.cleaned_data

        update = DLAScraperPendingOrganisationUpdate.objects.filter(pk=form_data['id']).first()

        if update.is_ipa:
            update.contract.ipa = update.proposed_organisation
            update.contract.save()
        else:
            update.contract.supplier = update.proposed_organisation
            update.contract.save()

        update.applied = True
        update.save()

        return JsonResponse({
            "status": True,
        }, status=200)


class DLAPendingUpdateIgnoreAjaxView(AdminPermissionsMixin, FormView):
    http_method_names = ['post']
    permission_required = ['administration.p_dla_contract_scrapper']
    form_class = DLAPendingOrganisationUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs() if super().get_form_kwargs() is not None else {}

        return kwargs

    def form_invalid(self, form, *args, **kwargs):
        return JsonResponse({
            "errors": form.errors,
        }, status=422)

    def form_valid(self, form, *args, **kwargs):
        form_data = form.cleaned_data

        update = DLAScraperPendingOrganisationUpdate.objects.filter(pk=form_data['id']).first()
        update.ignored = True
        update.save()

        return JsonResponse({
            "status": True,
        }, status=200)
