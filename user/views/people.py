import json

from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView
from bootstrap_modal_forms.mixins import is_ajax
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DetailView

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, get_datatable_organisation_status_badge, \
    get_datatable_person_positions, store_datatable_ordering, get_datatable_ordering
from organisation.models.organisation_people import OrganisationPeople, OrganisationPeopleHistory
from user.forms import PersonDetailsForm, PersonPositionFormSet
from user.mixins import AdminPermissionsMixin
from user.models import Person, PersonDetails, User


class PeopleListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = Person
    search_values_separator = '+'
    ordering_key = __qualname__.lower() + '_ordering'
    length_menu = [[20, 25, 50, 100, ], [20, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_order(self, request=None):
        default = [["last_name", "asc"]]

        return get_datatable_ordering(self, default)

    def get_initial_queryset(self, request=None):
        return Person.objects.filter(details__isnull=False).all()

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'title', 'title': 'Title', 'foreign_field': 'details__title__name', 'visible': True, },
        {'name': 'first_name', 'title': 'First Name', 'foreign_field': 'details__first_name', 'visible': True,
         'className': 'organisation_reg_name'},
        {'name': 'middle_name', 'title': 'Middle Name', 'foreign_field': 'details__middle_name', 'visible': True, },
        {'name': 'last_name', 'title': 'Last Name', 'foreign_field': 'details__last_name', 'visible': True, },
        {'name': 'current_positions', 'title': 'Current Position(s)', 'visible': True,
         'placeholder': True, 'searchable': False, 'orderable': False, 'width': '400px'},
        {'name': 'previous_positions', 'title': 'Previous Position(s)', 'visible': True,
         'placeholder': True, 'searchable': False, 'orderable': False, 'width': '400px'},
        {'name': 'status', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'organisation_status'},
    ]

    def sort_queryset(self, params, qs):
        store_datatable_ordering(self, params)

        return super().sort_queryset(params, qs)

    def customize_row(self, row, obj):
        row['current_positions'] = get_datatable_person_positions(
            obj.organisation_people)
        row['previous_positions'] = get_datatable_person_positions(
            obj.organisation_people_history)
        row['first_name'] = f'<span data-url="{obj.get_absolute_url()}">{obj.details.first_name}</span>'
        row['status'] = get_datatable_organisation_status_badge(obj.details.operational_status)
        return


class PeopleListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.p_contacts_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        header_buttons_list = [
            {'button_text': 'Add Person',
             'button_icon': 'fa-plus',
             'button_url': reverse('admin:person_create'),
             'button_modal': False,
             'button_perm': self.request.user.has_perm('core.p_contacts_create')},
        ]

        metacontext = {
            'title': 'People',
            'page_id': 'people_list',
            'page_css_class': 'clients_list datatable-clickable',
            'datatable_uri': 'admin:people_ajax',
            'header_buttons_list': json.dumps(header_buttons_list)
        }

        context['metacontext'] = metacontext
        return context


class PersonDetailsView(AdminPermissionsMixin, DetailView):
    template_name = 'person.html'
    model = Person
    context_object_name = 'person'
    permission_required = ['core.p_contacts_view']


class PersonCurrentPositionsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationPeople
    search_values_separator = '+'
    length_menu = [[10, 25, 50, 100, ], [10, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return OrganisationPeople.objects.filter(person_id=self.kwargs['person_id'])

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'job_title', 'title': 'Job Title', 'visible': True, 'width': '350px'},
        {'name': 'job_role', 'title': 'Job Role', 'foreign_field': 'role__name', 'visible': True, 'width': '350px'},
        {'name': 'organisation', 'title': 'Organisation', 'foreign_field': 'organisation__details__registered_name',
            'visible': True, 'width': '380px', 'className': 'organisation_reg_name'},
        {'name': 'is_decision_maker', 'visible': True, 'searchable': False, },
        {'name': 'start_date', 'title': 'Starting Date', 'visible': True, 'searchable': False},
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False, 'orderable': False},
    ]

    def customize_row(self, row, obj):
        row['organisation'] = (f'<span data-url="{obj.organisation.get_absolute_url()}">'
                               f'{obj.organisation.details.registered_name}</span>')
        row['start_date'] = obj.start_date.strftime("%Y-%m-%d")
        detach_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:organisation_people_detach',
                                                      kwargs={'organisation_people_id': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_popup='Leave Position',
                                                  button_modal=True,
                                                  modal_validation=False)
        row['actions'] = detach_btn
        return


class PersonPreviousPositionsListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationPeopleHistory
    search_values_separator = '+'
    initial_order = [["end_date", "desc"], ]
    length_menu = [[10, 25, 50, 100, ], [10, 25, 50, 100, ]]
    permission_required = ['core.p_contacts_view']

    def get_initial_queryset(self, request=None):
        return OrganisationPeopleHistory.objects.filter(
            person_id=self.kwargs['person_id'],
        )

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px'},
        {'name': 'job_title', 'title': 'Job Title', 'visible': True, 'width': '350px'},
        {'name': 'job_role', 'title': 'Job Role', 'foreign_field': 'role__name', 'visible': True, 'width': '350px'},
        {'name': 'organisation', 'title': 'Organisation', 'foreign_field': 'organisation__details__registered_name',
            'visible': True, 'width': '380px', 'className': 'organisation_reg_name'},
        {'name': 'is_decision_maker', 'visible': True, 'searchable': False, },
        {'name': 'start_date', 'visible': True, 'searchable': False, },
        {'name': 'end_date', 'visible': True, 'searchable': False, },
    ]

    def customize_row(self, row, obj):
        row['organisation'] = (f'<span data-url="{obj.organisation.get_absolute_url()}">'
                               f'{obj.organisation.details.registered_name}</span>')
        row['start_date'] = obj.start_date.strftime("%Y-%m-%d")
        row['end_date'] = obj.end_date.strftime("%Y-%m-%d")
        return


class PersonCreateView(AdminPermissionsMixin, TemplateView):
    template_name = 'person_create.html'

    person_id = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.person_id = self.kwargs.get('person_id', None)

    def has_permission(self):
        # Allow to create new person
        if not self.person_id and self.request.user.has_perm('core.p_contacts_create'):
            return True
        # Allow update existing person
        if self.person_id and self.request.user.has_perm('core.p_contacts_update'):
            return True

    def get(self, request, *args, **kwargs):
        if self.person_id:
            person = Person.objects.get(pk=self.person_id)
        else:
            person = Person()

        if hasattr(person, 'details'):
            person_details = person.details
        else:
            person_details = PersonDetails()

        return self.render_to_response({
            'person': person,
            'person_details_form': PersonDetailsForm(
                instance=person_details,
                prefix='person_details_form_pre'),

            'person_positions_formset': PersonPositionFormSet(
                person=person,
                request=self.request,
                prefix='person_positions_formset_pre'),
        })

    def post(self, request, *args, **kwargs):
        if self.person_id:
            person = Person.objects.get(pk=self.person_id)
        else:
            person = Person()

        person_details = PersonDetails()

        person_details_form = PersonDetailsForm(request.POST or None,
                                                instance=person_details,
                                                prefix='person_details_form_pre')

        person_positions_formset = PersonPositionFormSet(request.POST or None,
                                                         person=person,
                                                         request=self.request,
                                                         prefix='person_positions_formset_pre')

        # Process only if ALL forms are valid
        if all([
            person_details_form.is_valid(),
            person_positions_formset.is_valid(),
        ]):
            # Save Person object (for creating case)
            person.save()
            # Save Person details
            person_details = person_details_form.save(commit=False)
            person_details.person = person
            person_details.save()

            # Update person.details (needed to ability to send invitations email)
            person.details = person_details
            person.save()

            # Save Person Positions
            instances = person_positions_formset.save(commit=False)
            for instance in instances:
                instance.person = person
            person_positions_formset.save()
            person_positions_formset.save_m2m()

            # Create user for external access if username field filled
            username = person_details_form.cleaned_data.get('username', None)
            if username:
                user = User()
                user.username = username
                user.person = person
                user.save()
            else:
                user = getattr(person, 'user', None)

            if user:
                # Send invitation email if it applicable
                from user.utils.user_invitations import invite_external_user
                invite_external_user(user)

            return HttpResponseRedirect(reverse_lazy('admin:person', kwargs={'pk': person.pk}))
        else:
            # Render forms with errors
            return self.render_to_response({
                'person': person,
                'person_details_form': person_details_form,
                'person_positions_formset': person_positions_formset,
            })


class ExternalUserPasswordResetRequestView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['core.p_contacts_person_password_reset']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        metacontext = {
            'title': 'Sent Password Reset Email',
            'icon': 'fa-lock',
            'text': f'Email with the password reset URL for <b>{user.person.fullname}</b> will be sent to: '
                    f'<b>{user.person.details.contact_email}</b>',
            'action_button_text': 'Send',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context

    def form_valid(self, form, *args, **kwargs):
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            from user.utils.user_invitations import reset_external_user_password
            reset_external_user_password(user)
            messages.success(self.request, f'Password reset email sent')

        return super().form_valid(form)


class ExternalUserDeleteView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = User
    form_class = ConfirmationForm
    success_message = 'External access has been removed'

    def has_permission(self):
        # Process administration permission
        if self.request.user.has_perm('administration.p_staff_user_delete'):
            return True
        # Process permission for deleting by regular staff
        if self.request.user.has_perm('core.p_contacts_person_app_access_del'):
            if self.get_object().is_staff:
                return False
            return True

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        metacontext = {
            'title': 'Disable External User Access',
            'text': f'This action will remove external access user for {user.person.fullname}',
            'icon': 'fa-trash',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context
