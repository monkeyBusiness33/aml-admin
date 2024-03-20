from organisation.forms import GroundHandlerOpsPortalSettingsForm
from organisation.models import OrganisationOpsDetails

from django.urls import reverse
from django.views.generic import DetailView

from organisation.models import Organisation
from pricing.forms import FuelPricingCalculationFormSet


class MultiOrgDetailsViewMixin(DetailView):
    """
    Mixin to support additional type-dependent functionalities
    needed by organisation details view
    """
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        # Clear creation artifacts from session store on details page view
        request.session.pop(f'pending_types-{self.object.pk}', None)

        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = self.object

        # If the user is coming from list pages, set the appropriate tab to active
        prev_url = self.request.META.get('HTTP_REFERER')
        active_tab = ''

        if prev_url:
            if prev_url.endswith('aircraft_operators/'):
                active_tab = 'operator-details'
            elif prev_url.endswith('airports/'):
                active_tab = 'airport-details'
            elif prev_url.endswith('daos/'):
                active_tab = 'dao-details'
            elif prev_url.endswith('fuel_resellers/'):
                active_tab = 'fuel-seller-details'
            elif prev_url.endswith('ground_handlers/'):
                active_tab = 'handler-details'
            elif prev_url.endswith('ipas/'):
                active_tab = 'ipa-details'
            elif prev_url.endswith('oilcos/'):
                active_tab = 'oilco-details'
            elif prev_url.endswith('nasdls/'):
                active_tab = 'nasdl-details'
            elif prev_url.endswith('service_providers/'):
                active_tab = 'service-provider-details'
            elif prev_url.endswith('trip_support_companies/'):
                active_tab = 'trip-support-company-details'

        context['active_tab_from_origin'] = active_tab

        # Get details for dynamic edit btn (There's no edit pages for airports and DAO)
        context['edit_btn_data'] = {
            'dao-details': '',
            'airport-details': '',
            'organisation-details': reverse('admin:organisation_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'operator-details': reverse('admin:aircraft_operators_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'fuel-seller-details': reverse('admin:fuel_reseller_edit', kwargs={
                'organisation_id': self.kwargs['pk']}) if self.object.details.type_id in [2, 13] else '',
            'ipa-details': reverse('admin:ipa_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'handler-details': reverse('admin:ground_handler_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'oilco-details': reverse('admin:oilco_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'nasdl-details': reverse('admin:nasdl_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'service-provider-details': reverse('admin:service_provider_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
            'trip-support-company-details': reverse('admin:trip_support_company_edit', kwargs={
                'organisation_id': self.kwargs['pk']}),
        }

        # Get additional context for Airport orgs
        if getattr(organisation, 'airport_details', False):
            airport_other_based_organisations = Organisation.objects.airport_based_organisations(
                self.kwargs['pk'])
            context['airport_other_based_organisations'] = airport_other_based_organisations.exists()# Calculation-related functionality
            metacontext = {
                'page_id': 'fuel_pricing_calculation',
                'btn_text': 'Calculate Pricing Scenario',
                'form_submit_url': '{% url "admin:fuel_pricing" %}',
            }

            context['formset'] = FuelPricingCalculationFormSet(
                form_kwargs={'context': 'Airport', 'airport': organisation}
            )

            context['metacontext'] = metacontext
            context['context'] = 'Organisation'
            context['airport'] = getattr(organisation, 'pk', None)

        # Get additional context for Ground Handler orgs
        if getattr(organisation, 'handler_details', False):
            if hasattr(organisation, 'ops_details'):
                ops_details = getattr(organisation, 'ops_details')
            else:
                ops_details = OrganisationOpsDetails(organisation=organisation)

            ops_portal_settings_form = GroundHandlerOpsPortalSettingsForm(instance=ops_details, request=self.request)
            context['ops_portal_settings_form'] = ops_portal_settings_form

        return context
