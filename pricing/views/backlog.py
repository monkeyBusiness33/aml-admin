import json
import re

from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls.base import reverse_lazy
from django.views.generic import TemplateView
from bootstrap_modal_forms.generic import BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax

from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_actions_button
from organisation.models import Organisation, OrganisationContactDetails, OrganisationPeople
from pricing.forms import PricingUpdateRequestSend
from pricing.models import FuelIndexDetails, FuelAgreement, PricingBacklogEntry, FuelPricingMarketPld
from pricing.tasks import generate_pricing_update_request_email
from user.mixins import AdminPermissionsMixin


class FuelPricingBacklogAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = PricingBacklogEntry
    initial_order = [["priority", "asc"], ["expiry_date", "asc"], ]
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['pricing.p_view']

    column_defs = [
        {'name': 'type', 'title': 'Type', 'visible': True, 'orderable': True,
         'choices': (('M', 'Market Pricing'), ('S', 'Supplier Agreement'), ('I', 'Fuel Index Pricing')),
         'width': '150px', },
        {'name': 'name', 'title': 'Name / Reference', 'visible': True,
         'className': 'url_source_col single_cell_link', 'width': '300px'},
        {'name': 'supplier_name', 'title': 'Supplier', },
        {'name': 'locations_str', 'title': 'Location', 'orderable': False,
         'defaultContent': '--', },
        {'name': 'expiry_date', 'title': 'Expiry Date', 'searchable': False, },
        {'name': 'priority', 'title': 'Priority', 'searchable': False, },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'actions'},
    ]

    def get_initial_queryset(self, request=None):
        return None

    def get_filter_param(self, key):
        try:
            value = json.loads(self.request.POST.get('checkbox_filter_data'))[key]
        except:
            value = None

        return value

    def prepare_queryset(self, params, qs):
        """
        This function is called shortly after get_initial_queryset and is responsible for filtering and sorting.
        We can't filter after union, so in this case, we'll override this to do filtering on querysets separately.
        """
        expired_only = self.get_filter_param('expired_pricing_only')

        # Define initial partial querysets
        market_qs = FuelPricingMarketPld.objects.backlog_entries(expired_only)
        agreement_qs = FuelAgreement.objects.backlog_entries(expired_only)
        index_qs = FuelIndexDetails.objects.backlog_entries(expired_only)

        # Filter each of the partial querysets
        market_qs = self.filter_queryset(params, market_qs)
        agreement_qs = self.filter_queryset(params, agreement_qs)
        index_qs = self.filter_queryset(params, index_qs)

        # Join querysets
        qs = market_qs.union(agreement_qs).union(index_qs)

        # Sorting works fine after union
        qs = self.sort_queryset(params, qs)

        return qs

    def customize_row(self, row, obj):
        """
        Because union of querysets on different models is considered a queryset on the first model,
        and all objects are treated as object of that first class, here we can only use methods
        of the PricingBacklogEntry model, which is an Abstract Base Class for all involved models
        """
        row['type'] = obj.type_str
        row['name'] = (f'<span data-url="{obj.backlog_url}">'
                       f'{row["name"]}</span>')
        row['locations_str'] = obj.location_badges_str if row['locations_str'] else '--'
        row['expiry_date'] = obj.expiry_badge
        row['priority'] = obj.priority_badge

        view_btn = get_datatable_actions_button(
            button_text='',
            button_url=obj.backlog_url,
            button_class='fa-eye',
            button_active=self.request.user.has_perm('pricing.p_view')
        )

        update_request_btn = get_datatable_actions_button(
            button_text='',
            button_url=reverse_lazy('admin:send_fuel_pricing_update_request_email', kwargs={
                'organisation_id': obj.supplier_pk,
                'doc_type': 'pld' if obj.type == 'M' else 'agreement',
                'pk': obj.url_pk
            }),
            button_class='fa-envelope',
            button_active=obj.supplier_has_emails and self.request.user.has_perm(
                'pricing.p_send_pricing_update_request'),
            button_modal=True,
            modal_validation=True
        ) if obj.type in ['M', 'S'] else ''

        row['actions'] = view_btn + update_request_btn


class FuelPricingBacklogView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['pricing.p_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        header_checkbox_list = [
            {
                'checkbox_text': 'Expired Pricing Only',
                'checkbox_name': 'expired_pricing_only',
                'checkbox_value': True,
                'checkbox_perm': True,
            }
        ]

        metacontext = {
            'title': 'Pricing for Update',
            'page_id': 'fuel_pricing_backlog',
            'page_css_class': '',
            'datatable_uri': 'admin:fuel_pricing_backlog_ajax',
            'header_buttons_list': [],
            'header_checkbox_list': json.dumps(header_checkbox_list),
            'css_files': [
                static('css/backlog.css'),
            ],
        }

        context['metacontext'] = metacontext
        return context


class SendFuelPricingUpdateRequestEmailView(AdminPermissionsMixin, SuccessMessageMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = PricingUpdateRequestSend
    permission_required = ['pricing.p_send_pricing_update_request']

    doc_instance = None
    handling_request = None
    handler_email_addresses = []
    organisation = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.supplier = get_object_or_404(Organisation, pk=self.kwargs['organisation_id'])
        self.doc_type = 'Agreement' if kwargs['doc_type'] == 'agreement' else 'PLD'

        if self.doc_type == 'PLD':
            self.doc_instance = get_object_or_404(FuelPricingMarketPld, pk=self.kwargs['pk'])
        else:
            self.doc_instance = get_object_or_404(FuelAgreement, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'handler_email_addresses': [],
            'supplier': self.supplier,
            'doc_type': self.doc_type,
            'doc_instance': self.doc_instance,
        })
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': f'Send Pricing Update Request',
            'icon': 'fa-sticky-note',
            'text': f'Please specify the recipient details for the auto-generated pricing update request email to'
                    f' <b>{self.supplier.full_repr}</b> for {self.doc_type} <b>"{self.doc_instance}"</b>',
            'action_button_text': 'Send',
            'action_button_class': 'btn-success',
            'cancel_button_class': 'btn-gray-200',
            'form_id': 'send_handling_request_to_handler',
            'js_scripts': [
                static('assets/js/select2_modal_formset.js'),
                static('js/send_pricing_update_request.js')
            ]
        }

        context['metacontext'] = metacontext

        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            request_person = getattr(self.request.user, 'person')
            send_to_people = form.cleaned_data['send_to_people']
            additional_emails = form.cleaned_data['additional_emails']
            locations_fuel_dict = {}

            if additional_emails == ['']:
                additional_emails = []

            send_to_emails = {
                'to': set(), 'cc': set(), 'bcc': set()
            }

            # Get fuel types for all selected locations
            for location in form.cleaned_data['locations']:
                fuel_types = sorted(list(self.doc_instance.get_fuel_types_at_location(location)))
                locations_fuel_dict[location.airport_details.icao_iata] = fuel_types

            # Process the Recipients field
            for contact_details_pk in send_to_people:
                # If the position had no additional contact entry for this email
                # (id starts with "new_from_pos_"), create a new entry for the pair
                if contact_details_pk.startswith('new_from_pos_'):
                    position_pk = re.search(r'\d+', contact_details_pk).group(0)
                    position = get_object_or_404(OrganisationPeople, pk=position_pk)

                    contact_details = OrganisationContactDetails.objects.create(
                        organisation=self.supplier,
                        organisations_people=position,
                        email_address=position.contact_email,
                        description="TBC (Auto-Created)",
                        supplier_include_for_fuel_pricing_updates=True,
                        address_cc=True,
                        updated_by=request_person,
                    )
                else:
                    contact_details = get_object_or_404(OrganisationContactDetails, pk=contact_details_pk)

                    # If existing contact was never used for this purpose, mark it for future use
                    if not contact_details.supplier_include_for_fuel_pricing_updates:
                        contact_details.supplier_include_for_fuel_pricing_updates = True
                        contact_details.save()

                if getattr(contact_details, 'email_address', None):
                    if contact_details.address_to:
                        send_to_emails['to'].add(contact_details.email_address)
                    elif contact_details.address_cc:
                        send_to_emails['cc'].add(contact_details.email_address)
                    elif contact_details.address_bcc:
                        send_to_emails['bcc'].add(contact_details.email_address)

            # Process additional emails
            existing_emails = {k: v for v, k in (self.supplier.organisation_contact_details.filter(
                organisations_people__isnull=True).values_list('pk', 'email_address'))}

            for email_tag in additional_emails:
                field, email, desc = re.search(
                    r'^(TO:|CC:|BCC:)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\s?(\(.*\))?$',
                    email_tag
                ).groups()

                if not field:
                    field = 'CC:'

                # Check if the email is new
                if email not in existing_emails:
                    # Create new contact details for email
                    contact_details = OrganisationContactDetails.objects.create(
                        organisation=self.supplier,
                        email_address=email,
                        description=desc[1:-1] if desc else "TBC (Auto-Created)",
                        supplier_include_for_fuel_pricing_updates=True,
                        address_to=field == 'TO:',
                        address_cc=field == 'CC:',
                        address_bcc=field == 'BCC:',
                        updated_by=request_person,
                    )
                else:
                    # If email was never used for this purpose, mark it for future use
                    contact_details = get_object_or_404(OrganisationContactDetails, pk=existing_emails[email])
                    contact_details.supplier_include_for_fuel_pricing_updates = True
                    contact_details.save()

                if field == 'TO:':
                    send_to_emails['to'].add(email)
                elif field == 'CC:':
                    send_to_emails['cc'].add(email)
                elif field == 'BCC:':
                    send_to_emails['bcc'].add(email)

            for field, emails in send_to_emails.items():
                send_to_emails[field] = sorted(list(emails))

            generate_pricing_update_request_email.delay(
                sender_email='fuel-pricing@amlglobal.net',
                send_to=send_to_emails,
                requesting_person_id=request_person.pk,
                locations_fuel_dict=locations_fuel_dict,
            )

            # self.handling_request.activity_log.create(
            #     author=request_person,
            #     record_slug='sfr_ground_handling_submitted',
            #     details='Handling Request: Submitted',
            # )

        return super().form_valid(form)
