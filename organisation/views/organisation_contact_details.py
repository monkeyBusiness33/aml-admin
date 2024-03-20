from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalUpdateView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button
from organisation.forms import OrganisationContactDetailsEditForm, OrganisationContactDetailsFormSet
from organisation.models import OrganisationContactDetails, OrganisationContactDetailsLocation, Organisation
from user.mixins import AdminPermissionsMixin


class OrganisationContactDetailsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationContactDetails
    search_values_separator = '+'
    permission_required = ['core.p_contacts_additional_contact_details_view']

    def get_initial_queryset(self, request=None):
        qs = OrganisationContactDetails.objects.with_details().filter(
            organisation_id=self.kwargs['organisation_id'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False,
         'orderable': False, 'width': '10px'},
        {'name': 'person', 'title': 'Person', 'defaultContent': '--', 'className': 'url_source_col single_cell_link', },
        {'name': 'description', 'title': 'Description', 'defaultContent': '--', },
        {'name': 'locations_str', 'title': 'Applicable Location(s)', 'orderable': False, 'placeholder': True,
         'defaultContent': '--'},
        {'name': 'email_address', 'title': 'Email Address', 'defaultContent': '--', },
        {'name': 'phone_number', 'title': 'Phone Number', 'defaultContent': '--', },
        {'name': 'included_in', 'title': 'Included In', 'placeholder': True, 'searchable': False,
         'orderable': False, },
        {'name': 'actions', 'title': '', 'visible': True,
         'placeholder': True, 'searchable': False, 'orderable': False, 'className': 'actions_column'},
    ]

    def customize_row(self, row, obj):
        if obj.organisations_people:
            url = obj.organisations_people.person.get_absolute_url()
            row['person'] = f'<span data-url={url}>{row["person"]}</span>'

        row['locations_str'] = obj.location_badges_str

        if obj.email_address:
            row['email_address'] = f"{obj.email_fields_icon_str}{row['email_address']}"

        if obj.phone_number:
            row['phone_number'] += obj.phone_number_icons_str

        row['included_in'] = obj.included_in_choices_str

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:organisation_contact_details_edit', kwargs={
                                                        'organisation_id': self.kwargs['organisation_id'],
                                                        'pk': obj.pk
                                                    }),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'core.p_contacts_additional_contact_details_update'),
                                                button_modal=True,
                                                modal_validation=True)
        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:organisation_contact_details_delete', kwargs={
                                                          'organisation_id': self.kwargs['organisation_id'],
                                                          'pk': obj.pk
                                                      }),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm(
                                                      'core.p_contacts_additional_contact_details_delete'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] = edit_btn + delete_btn
        return


class OrganisationContactDetailsCreateView(AdminPermissionsMixin, SuccessMessageMixin, TemplateView):
    template_name = 'organisation_contact_details_create.html'
    success_message = 'Contact Details created successfully'
    permission_required = ['core.p_contacts_additional_contact_details_create']

    def get_success_url(self, organisation):
        return organisation.get_absolute_url()

    def get(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.kwargs.get('organisation_id', None))

        return self.render_to_response({
            'organisation': organisation,
            'contact_details_formset': OrganisationContactDetailsFormSet(
                organisation=organisation,
                form_kwargs={'organisation': organisation},
                prefix='contact_details_formset'),
        })

    def post(self, request, *args, **kwargs):
        organisation = Organisation.objects.get(pk=self.kwargs.get('organisation_id', None))

        contact_details_formset = OrganisationContactDetailsFormSet(request.POST or None,
                                                                    organisation=organisation,
                                                                    form_kwargs={'organisation': organisation},
                                                                    prefix='contact_details_formset')

        if contact_details_formset.is_valid():
            # Save updated data
            for form in contact_details_formset:
                if not form.has_changed() or form.cleaned_data.get('DELETE'):
                    continue

                instance = form.save(commit=False)
                instance.organisation = organisation
                instance.comms_settings_client = form.cleaned_data.get('comms_settings_client', [])
                instance.comms_settings_supplier = form.cleaned_data.get('comms_settings_supplier', [])

            contact_details_formset.save()

            return HttpResponseRedirect(self.get_success_url(organisation))
        else:
            # Render forms with errors
            return self.render_to_response({
                'organisation': organisation,
                'contact_details_formset': contact_details_formset,
            })


class OrganisationContactDetailsEditView(AdminPermissionsMixin, BSModalUpdateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = OrganisationContactDetails
    form_class = OrganisationContactDetailsEditForm
    success_message = 'Contact details updated successfully'
    permission_required = ['core.p_contacts_additional_contact_details_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'organisation': self.object.organisation})

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Contact Details',
            'icon': 'fa-edit',
            'js_scripts': [
                static('assets/js/select2_modal_formset.js'),
                static('js/organisation_contact_details_edit.js')
            ]
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form):
        # Save comms settings
        data = form.cleaned_data
        form.instance.comms_settings_client = data.get('comms_settings_client', [])
        form.instance.comms_settings_supplier = data.get('comms_settings_supplier', [])

        return super().form_valid(form)


class OrganisationContactDetailsDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationContactDetails
    form_class = ConfirmationForm
    success_message = 'Contact details have been deleted'
    permission_required = ['core.p_contacts_additional_contact_details_delete']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Delete Contact Details',
            'text': f'Are you sure you want to delete this set of contact details?',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger'
        }

        context['metacontext'] = metacontext
        return context
