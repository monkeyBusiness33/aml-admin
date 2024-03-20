from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalDeleteView
from bootstrap_modal_forms.mixins import PassRequestMixin, is_ajax
from django.conf import settings
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from ajax_datatable.views import AjaxDatatableView
from django.views.generic import TemplateView, DetailView, FormView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_organisation_status_badge
from dla_scraper.utils.scraper import reconcile_org_name
from handling.models import HandlingRequestPassengersPayload
from organisation.forms import GroundHandlerOpsPortalSettingsForm, OrganisationDetailsForm, OrganisationRestictedForm, \
    HandlerDetailsForm, OrganisationAddressFormSet, GroundHandlerFuelTypeForm, HandlerCancellationBandForm, \
    HandlerCancellationBandTermBaseFormSet, HandlerCancellationBandTermForm
from organisation.mixins import MultiOrgDetailsViewMixin
from organisation.models import Organisation, OrganisationOpsDetails, OrganisationDetails, OrganisationRestricted, \
    HandlerDetails, IpaLocation, IpaDetails, HandlerCancellationBand, HandlerCancellationBandTerm
from organisation.views.base import OrganisationCreateEditMixin
from user.mixins import AdminPermissionsMixin
import json


class GroundHandlersListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Organisation
    search_values_separator = '+'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return Organisation.objects.handling_agent_with_airport_details()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px' },
        {'name': 'registered_name', 'title': 'Registered Name', 'foreign_field': 'details__registered_name',
         'visible': True, 'className': 'organisation_link'},
        {'name': 'trading_name', 'title': 'Trading Name', 'foreign_field': 'details__trading_name', 'visible': True},
        {'name': 'handling_brand', 'title': 'Handling Brand',
         'foreign_field': 'details__department_of__details__registered_name', 'visible': True, },
        {'name': 'icao_iata', 'title': 'Location', 'visible': True, 'className': 'airport_link'},
        {'name': 'handler_type', 'title': 'Handler Type', 'foreign_field': 'handler_details__handler_type__name',
         'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'country', 'title': 'Country', 'foreign_field': 'details__country__name',
         'visible': True, 'choices': True, 'autofilter': True, },
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True,
            'searchable': False, 'orderable': False, 'className': 'organisation_status'},
    ]

    def customize_row(self, row, obj):
        row['icao_iata'] = (f'<span data-url="{obj.handler_details.airport.get_absolute_url()}">'
                               f'{obj.handler_details.airport.airport_details.icao_code}</span>')
        row['registered_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.registered_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.operational_status)
        return


class GroundHandlersListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add New Ground Handler',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:ground_handler_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'Ground Handlers',
            'page_id': 'ground_handlers_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:ground_handlers_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class GroundHandlerDetailsView(AdminPermissionsMixin, MultiOrgDetailsViewMixin):
    template_name = 'organisation_details.html'
    model = Organisation
    context_object_name = 'organisation'
    permission_required = ['core.p_contacts_view']

    def get_queryset(self):
        return self.model.objects.handling_agent()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        handler = self.get_object()
        context['cancellation_terms'] = HandlerCancellationBandTerm.objects.filter(cancellation_band__handler=handler)
        return context


class GroundHandlerOpsDetailsUpdateView(AdminPermissionsMixin, PassRequestMixin, FormView):
    template_name = 'includes/_modal_form.html'
    form_class = GroundHandlerOpsPortalSettingsForm
    permission_required = ['core.p_contacts_update']

    organisation = None
    instance = None

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = Organisation.objects.get(pk=self.kwargs['organisation_id'])

        try:
            self.instance = OrganisationOpsDetails.objects.get(organisation=self.organisation)
        except OrganisationOpsDetails.DoesNotExist:
            self.instance = OrganisationOpsDetails(organisation=self.organisation)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'instance': self.instance})
        return kwargs

    def form_valid(self, form, *args, **kwargs):
        form.save()

        message_text = ''
        if 'receives_parking_chase_email' in form.changed_data:
            if form.instance.receives_parking_chase_email is True:
                message_text = 'Parking Chase Emails will be sent to the organisation email address'
            else:
                message_text = 'Parking Chase Emails disabled'

        if 'spf_use_aml_logo' in form.changed_data:
            if form.instance.spf_use_aml_logo is True:
                message_text = 'AML logo will be displayed in the SPF documents'
            else:
                message_text = 'Ground Handler logo will be displayed in the SPF documents'

        response = {
            'message': message_text,
        }

        return JsonResponse(response)


class GroundHandlerCreateEditView(OrganisationCreateEditMixin, AdminPermissionsMixin, TemplateView):
    template_name = 'ground_handler_edit.html'
    permission_required = ['organisation.change_handler']

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)

        if hasattr(organisation, 'handler_details'):
            handler_details = organisation.handler_details
        else:
            handler_details = HandlerDetails()

        return self.render_to_response({
            'organisation': organisation,
            'handler_details_form': HandlerDetailsForm(
                instance=handler_details,
                prefix='handler_details_form_pre',),
            })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.organisation_id)
        handler_details = getattr(organisation, 'handler_details', HandlerDetails())

        handler_details_form = HandlerDetailsForm(request.POST or None,
                                                  instance=handler_details,
                                                  prefix='handler_details_form_pre')

        # Process only if ALL forms are valid
        if all([
            handler_details_form.is_valid(),
        ]):
            handler_details = handler_details_form.save(commit=False)
            handler_details.organisation = organisation
            handler_details.save()

            # Save Handler IPA Details and location if is_ipa ticked
            handler_is_ipa = handler_details_form.cleaned_data.get('is_ipa', False)
            if handler_is_ipa is True:
                handler_is_ipa, created = IpaDetails.objects.get_or_create(
                    organisation=organisation)
                organisation.ipa_locations.set([handler_details.airport], clear=True)
            else:
                IpaDetails.objects.filter(organisation=organisation).delete()
                IpaLocation.objects.filter(organisation=organisation).delete()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'handler_details_form': handler_details_form,
                })


class GroundHandlerFuelTypesUpdateView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = IpaLocation
    form_class = GroundHandlerFuelTypeForm
    slug_field = 'organisation_id'
    slug_url_kwarg = "organisation_id"
    success_message = 'Fuel Types updated successfully'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Update Ground Handler Fuel Types',
            'text': 'As soon current ground handler represented as IPA too, you can adjust dispensed fuel types in '
                    'based airport',
            'icon': 'fa-gas-pump',
        }

        context['metacontext'] = metacontext
        return context


class HandlerCancellationBandView(AdminPermissionsMixin, TemplateView):
    template_name = 'organisations_pages_includes/_handler_cancellation_terms_modal.html'
    permission_required = ['core.p_contacts_update']

    organisation = None
    handler_cancellation_band = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        cancellation_band_id = self.kwargs.get('cancellation_band_id')
        organisation_id = self.kwargs.get('organisation_id')

        if cancellation_band_id:
            self.handler_cancellation_band = HandlerCancellationBand.objects.get(pk=self.kwargs['cancellation_band_id'])
            self.organisation = self.handler_cancellation_band.handler
        else:
            self.organisation = Organisation.objects.get(pk=organisation_id)
            self.handler_cancellation_band = HandlerCancellationBand(handler=self.organisation)

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_metacontext(self):
        metacontext = {
            'title': 'Add Cancellation Term',
            'action_button_class': 'btn-secondary',
            'action_button_text': 'Submit',
        }
        return metacontext

    def cancellation_terms_formset(self):
        return modelformset_factory(
            HandlerCancellationBandTerm,
            min_num=4,
            extra=15,
            can_delete=True,
            form=HandlerCancellationBandTermForm,
            formset=HandlerCancellationBandTermBaseFormSet,
            fields=['penalty_specific_service', 'penalty_percentage', 'penalty_amount', 'penalty_amount_currency', ]
        )

    def get(self, request, *args, **kwargs):
        return self.render_to_response({
            'organisation': self.organisation,
            'metacontext': self.get_metacontext(),
            'handler_cancellation_band_form': HandlerCancellationBandForm(
                instance=self.handler_cancellation_band,
                prefix='handler_cancellation_band_form_pre'),
            'cancellation_terms_formset': self.cancellation_terms_formset()(
                handler_cancellation_band=self.handler_cancellation_band,
                prefix='cancellation_terms_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        handler_cancellation_band_form = HandlerCancellationBandForm(
            request.POST or None,
            instance=self.handler_cancellation_band,
            prefix='handler_cancellation_band_form_pre',
        )

        cancellation_terms_formset = self.cancellation_terms_formset()(
            request.POST or None,
            handler_cancellation_band=self.handler_cancellation_band,
            prefix='cancellation_terms_formset_pre',
        )

        # Process only if ALL forms are valid
        if all([
            handler_cancellation_band_form.is_valid(),
            cancellation_terms_formset.is_valid(),
        ]):
            if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                handler_cancellation_band = handler_cancellation_band_form.save()

                instances = cancellation_terms_formset.save(commit=False)
                for instance in instances:
                    instance.cancellation_band = handler_cancellation_band
                cancellation_terms_formset.save()

                self.organisation.activity_log.create(
                    record_slug='organisation_cancellation_terms_updated',
                    author=getattr(self, 'person'),
                    details='Handler cancellation terms has bee updated'
                )

            return HttpResponseRedirect(self.get_success_url())
        else:
            if settings.DEBUG:
                print(
                    handler_cancellation_band_form.errors if handler_cancellation_band_form else '',
                    cancellation_terms_formset.errors if cancellation_terms_formset else '',
                )
            # Render forms with errors
            return self.render_to_response({
                'metacontext': self.get_metacontext(),
                'handler_cancellation_band_form': handler_cancellation_band_form,
                'cancellation_terms_formset': cancellation_terms_formset,
            })


class HandlerCancellationBandDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = HandlerCancellationBand
    form_class = ConfirmationForm
    success_message = 'Cancellation Term successfully removed'
    permission_required = ['core.p_contacts_update']
    pk_url_kwarg = "cancellation_band_id"

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Remove Handler Cancellation Term',
            'text': f'Please confirm cancellation term removal',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context
