from bootstrap_modal_forms.mixins import is_ajax
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from organisation.forms import OrganisationTypeSelectForm, OrganisationDetailsForm, OrganisationRestictedForm, \
    FuelResellerDetailsForm, HandlerDetailsForm, NasdlDetailsForm, OperatorDetailsForm, OrganisationAircraftTypesForm
from organisation.models import Organisation, OrganisationDetails, OrganisationRestricted, IpaDetails
from user.mixins import AdminPermissionsMixin


class PersonPositionCreateOrganisationView(AdminPermissionsMixin, TemplateView):
    template_name = 'person_positions_add_organisation_modal.html'
    permission_required = ['core.p_contacts_create']

    def get(self, request, *args, **kwargs):
        organisation = Organisation()
        organisation_details = OrganisationDetails()
        organisation_restricted = OrganisationRestricted()

        return self.render_to_response({
            'organisation': organisation,

            'organisation_type_form': OrganisationTypeSelectForm(
                instance=organisation_details,
                prefix='organisation_type_form_pre'),

            'organisation_details_form': OrganisationDetailsForm(
                instance=organisation_details,
                prefix='organisation_details_form_pre',
                context='create_from_person'),

            'organisation_restricted_form': OrganisationRestictedForm(
                instance=organisation_restricted,
                prefix='organisation_restricted_form_pre',),

            'fuel_reseller_details_form': FuelResellerDetailsForm(
                organisation=organisation,
                prefix='fuel_reseller_details_form_pre',),

            'handler_details_form': HandlerDetailsForm(
                prefix='handler_details_form_pre',),

            'nasdl_details_form': NasdlDetailsForm(
                prefix='nasdl_details_form_pre'),

            'operator_details_form': OperatorDetailsForm(
                prefix='operator_details_form_pre',),

            })

    def post(self, request, *args, **kwargs):
        organisation = Organisation()
        organisation_type_form = OrganisationTypeSelectForm(request.POST or None,
                                                            prefix='organisation_type_form_pre')
        organisation_type_form.is_valid()
        organisation_details_w_type = organisation_type_form.save(commit=False)
        organisation_details_w_type.updated_by = getattr(self, 'person')
        organisation_type = organisation_type_form.cleaned_data.get('type')

        organisation_details_form = OrganisationDetailsForm(request.POST or None,
                                                            instance=organisation_details_w_type,
                                                            prefix='organisation_details_form_pre',
                                                            context='create_from_person')

        organisation_aircraft_types_form = OrganisationAircraftTypesForm(request.POST or None,
                                                                         prefix='organisation_aircraft_types_form_pre')

        organisation_restricted_form = OrganisationRestictedForm(request.POST or None,
                                                                 prefix='organisation_restricted_form_pre')

        operator_details_form = OperatorDetailsForm(request.POST or None,
                                                    prefix='operator_details_form_pre')

        fuel_reseller_details_form = FuelResellerDetailsForm(request.POST or None,
                                                             organisation=organisation,
                                                             prefix='fuel_reseller_details_form_pre')

        handler_details_form = HandlerDetailsForm(request.POST or None,
                                                  prefix='handler_details_form_pre')

        nasdl_details_form = NasdlDetailsForm(request.POST or None,
                                              prefix='nasdl_details_form_pre')

        if organisation_type.pk == 1:
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
                organisation_aircraft_types_form.is_valid(),
                operator_details_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # # Save Organisation details
                    organisation_details = organisation_details_form.save()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    organisation_restricted = organisation_restricted_form.save(commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    operator_details = operator_details_form.save(commit=False)
                    operator_details.organisation = organisation
                    operator_details.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
            else:
                # Render forms with errors
                return self.render_to_response({
                    'organisation_details_form': organisation_details_form,
                    'organisation_restricted_form': organisation_restricted_form,
                    'operator_details_form': operator_details_form,
                })
        elif organisation_type.pk == 2:
            # Fuel Reseller
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
                fuel_reseller_details_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # Save Organisation details
                    organisation_details = organisation_details_form.save()

                    if fuel_reseller_details_form.cleaned_data['is_fuel_agent']:
                        organisation_details.type_id = 13
                    else:
                        organisation_details.type_id = 2

                    # Create Organisation object
                    organisation = Organisation()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    # Create Organisation Restricted object
                    organisation_restricted = organisation_restricted_form.save(
                        commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
        elif organisation_type.pk == 3:
            # Ground Handler
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
                handler_details_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # # Save Organisation details
                    organisation_details = organisation_details_form.save()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    # Create Organisation Restricted object
                    organisation_restricted = organisation_restricted_form.save(commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    # Create and Handling Agent Details
                    handler_details = handler_details_form.save(commit=False)
                    handler_details.organisation = organisation
                    handler_details.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
            else:
                # Render forms with errors
                return self.render_to_response({
                    'organisation_details_form': organisation_details_form,
                    'organisation_restricted_form': organisation_restricted_form,
                    'handler_details_form': handler_details_form,
                })
        elif organisation_type.pk == 4:
            # Into-Plane Agent
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # # Save Organisation details
                    organisation_details = organisation_details_form.save()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    # Create IpaDetails object
                    ipa_details = IpaDetails()
                    ipa_details.organisation = organisation
                    ipa_details.save()

                    # Create Organisation Restricted object
                    organisation_restricted = organisation_restricted_form.save(
                        commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
            else:
                # Render forms with errors
                return self.render_to_response({
                    'organisation_details_form': organisation_details_form,
                    'organisation_restricted_form': organisation_restricted_form,
                })
        elif organisation_type.pk == 1002:
            # NASDL
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
                nasdl_details_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # # Save Organisation details
                    organisation_details = organisation_details_form.save()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    # Create Organisation Restricted object
                    organisation_restricted = organisation_restricted_form.save(
                        commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    # Create NASDL Details object
                    nasdl_details = nasdl_details_form.save(commit=False)
                    nasdl_details.organisation = organisation
                    nasdl_details.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
            else:
                # Render forms with errors
                return self.render_to_response({
                    'organisation_details_form': organisation_details_form,
                    'organisation_restricted_form': organisation_restricted_form,
                    'nasdl_details_form': nasdl_details_form,
                })
        else:
            # Fallback for organisation type without specific "Details" form
            # id: 5 - Oil Company
            # id: 11 - Trip Support
            # id: 14 - Service Providers
            if all([
                organisation_details_form.is_valid(),
                organisation_restricted_form.is_valid(),
            ]):
                if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
                    # # Save Organisation details
                    organisation_details = organisation_details_form.save()
                    organisation.details = organisation_details
                    organisation.save()

                    organisation_details.organisation = organisation
                    organisation_details.save()

                    # Create Organisation Restricted object
                    organisation_restricted = organisation_restricted_form.save(
                        commit=False)
                    organisation_restricted.organisation = organisation
                    organisation_restricted.save()

                    # Trigger organisation post_save signal to assign tags regarding created details tables
                    from django.db.models.signals import post_save
                    post_save.send(Organisation, instance=organisation)
                return HttpResponseRedirect(self.request.META.get('HTTP_REFERER'))
            else:
                # Render forms with errors
                return self.render_to_response({
                    'organisation_details_form': organisation_details_form,
                    'organisation_restricted_form': organisation_restricted_form,
                })
