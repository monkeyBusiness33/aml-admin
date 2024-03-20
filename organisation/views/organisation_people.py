from ajax_datatable.views import AjaxDatatableView
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalUpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls.base import reverse_lazy

from core.forms import ConfirmationForm
from core.utils.datatables_functions import get_datatable_actions_button, \
    store_datatable_ordering, get_datatable_ordering, get_fontawesome_icon
from organisation.forms import OrganisationPersonForm
from organisation.models import OrganisationPeople, Organisation
from user.mixins import AdminPermissionsMixin
from user.models import PersonDetails


class OrganisationPeopleListAjaxView(AdminPermissionsMixin, AjaxDatatableView):
    model = OrganisationPeople
    search_values_separator = '+'
    permission_required = ['core.p_contacts_view']

    organisation = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(Organisation, pk=self.kwargs['pk'])

    def get_initial_order(self, request=None):
        default = [["full_name", "asc"]]

        return get_datatable_ordering(self, default)

    def get_initial_queryset(self, request=None):
        qs = OrganisationPeople.objects.filter(
                organisation_id=self.kwargs['pk'])
        return qs

    column_defs = [
        {'name': 'id', 'title': 'ID', 'visible': False, 'orderable': False, 'width': '10px', },
        {'name': 'title', 'title': 'Title', 'foreign_field': 'person__details__title__name', 'visible': True,
         'width': '20px', },
        {'name': 'full_name', 'title': 'Name', 'foreign_field': 'person__details__first_name',
            'visible': True, 'className': 'organisation_reg_name'},
        {'name': 'job_title', 'title': 'Job Title', 'visible': True, },
        {'name': 'role', 'title': 'Role', 'foreign_field': 'role__name', 'visible': True, },
        {'name': 'is_authorising_person', 'title': 'Authorising Person', 'visible': True,
         'searchable': False, 'width': '50px', },
        {'name': 'actions', 'title': '', 'visible': True, 'placeholder': True, 'searchable': False,
         'orderable': False, 'className': 'actions'},
    ]

    def get_column_defs(self, request):
        for column in self.column_defs:
            if column['name'] == 'is_authorising_person':
                column['title'] = self.organisation.authorising_person_role_name
        return self.column_defs

    def sort_queryset(self, params, qs):
        store_datatable_ordering(self, params)

        return super().sort_queryset(params, qs)

    def customize_row(self, row, obj):
        row['full_name'] = f'<span data-url="{obj.person.get_absolute_url()}">{obj.person.fullname}</span>'

        if obj.is_authorising_person:
            row['is_authorising_person'] = get_fontawesome_icon(icon_name='check')
        else:
            row['is_authorising_person'] = ''

        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:organisation_people_edit',
                                                    kwargs={'organisation_people_id': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                button_modal=True,
                                                modal_validation=True)

        detach_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:organisation_people_detach',
                                                      kwargs={'organisation_people_id': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.p_contacts_update'),
                                                  button_modal=True,
                                                  modal_validation=False)
        row['actions'] = edit_btn + detach_btn
        return


class OrganisationPersonCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = PersonDetails
    form_class = OrganisationPersonForm
    success_message = 'Person created successfully'
    permission_required = ['core.p_contacts_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        organisation_id = self.kwargs.get('organisation_id', None)
        organisation = get_object_or_404(Organisation, pk=organisation_id)
        kwargs.update({'organisation': organisation})

        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Add New Person',
            'icon': 'fa-user-plus',
        }

        context['metacontext'] = metacontext
        return context


class OrganisationPersonEditView(AdminPermissionsMixin, BSModalUpdateView):
    template_name = 'includes/_modal_form.html'
    model = PersonDetails
    form_class = OrganisationPersonForm
    success_message = 'Person details updated successfully'
    permission_required = ['core.p_contacts_update']

    organisation_people = None

    def get_object(self, queryset=None):
        self.organisation_people = get_object_or_404(
            OrganisationPeople, pk=self.kwargs['organisation_people_id'])
        return self.organisation_people.person.details

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'organisation': self.organisation_people.organisation})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Person Details',
            'icon': 'fa-user-edit',
        }

        context['metacontext'] = metacontext
        return context


class OrganisationPersonDetachView(AdminPermissionsMixin, SuccessMessageMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = OrganisationPeople
    form_class = ConfirmationForm
    pk_url_kwarg = 'organisation_people_id'
    success_message = 'Person detached'
    permission_required = ['core.p_contacts_update']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Leave Position',
            'text': f'Are you certain you want to proceed with updating this person’s employment history?',
            'icon': 'fa-user-minus',
            'action_button_text': 'Yes',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context
