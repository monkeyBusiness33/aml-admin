from bootstrap_modal_forms.mixins import is_ajax
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models import Count, Case, Q, When, BooleanField
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, FormView

from administration.forms.users_and_roles import StaffUserForm, StaffPersonDetailsForm, StaffPersonPositionForm
from core.forms import ConfirmationForm
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView

from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_fontawesome_icon, get_datatable_actions_button
from organisation.models import OrganisationPeople
from user.mixins import AdminPermissionsMixin
from django.urls import reverse_lazy
from django.contrib import messages

from user.models import User, Person, PersonDetails


class StaffUsersListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = User
    permission_required = ['administration.p_view']
    search_values_separator = '+'
    length_menu = [[10, 50, 100, 250, -1], [10, 50, 100, 250, 'all']]

    def get_initial_queryset(self, request=None):
        return User.objects.filter(is_staff=True).annotate(
            perms_count=Count('user_permissions')
        ).distinct()

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'searchable': False, 'orderable': True, 'width': 30, },
        {'name': 'username', 'visible': True, },
        {'name': 'name', 'title': 'Full Name', 'foreign_field': 'person__details__first_name', 'visible': True, },
        {'name': 'email_address', 'title': 'Email Address', 'foreign_field': 'person__details__contact_email',
         'visible': True, 'choices': False, },
        {'name': 'roles', 'title': 'Roles', 'm2m_foreign_field': 'roles__name', 'visible': True, },
        {'name': 'perms_count', 'title': 'Perms', 'visible': True, },
        {'name': 'is_active', 'title': 'Active', 'choices': True, },
        {'name': 'actions', 'title': 'Actions', 'placeholder': True, 'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['name'] = getattr(obj.person, 'fullname')

        if obj.is_active:
            row['is_active'] = get_fontawesome_icon(icon_name='check-circle text-success', tooltip_text="Active")
        else:
            row['is_active'] = get_fontawesome_icon(icon_name='ban text-danger', tooltip_text="Suspended")

        row['actions'] = ''
        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:staff_user_update', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'administration.p_staff_user_edit'),
                                                button_modal=True,
                                                button_modal_size='#modal-lg',
                                                modal_validation=True)

        row['actions'] += edit_btn

        perms_btn = get_datatable_actions_button(button_text='',
                                                 button_url=reverse_lazy(
                                                     'admin:staff_user_permissions', kwargs={'pk': obj.pk}),
                                                 button_class='fa-cogs',
                                                 button_active=self.request.user.has_perm('core.x_super_admin'),
                                                 button_modal=False)
        row['actions'] += perms_btn

        if obj.is_active:
            suspend_btn = get_datatable_actions_button(button_text='',
                                                       button_url=reverse_lazy(
                                                           'admin:user_suspend', kwargs={'pk': obj.pk}),
                                                       button_class='fa-user-lock text-danger',
                                                       button_popup="Suspend User",
                                                       button_active=self.request.user.has_perm(
                                                           'administration.p_staff_user_suspend'),
                                                       button_modal=True,
                                                       modal_validation=True)
        else:
            suspend_btn = get_datatable_actions_button(button_text='',
                                                       button_url=reverse_lazy(
                                                           'admin:user_suspend', kwargs={'pk': obj.pk}),
                                                       button_class='fa-user-lock text-success',
                                                       button_popup="Activate User",
                                                       button_active=self.request.user.has_perm(
                                                           'administration.p_staff_user_suspend'),
                                                       button_modal=True,
                                                       modal_validation=True)

        row['actions'] += suspend_btn

        reset_qr_btn = get_datatable_actions_button(button_text='',
                                                    button_url=reverse_lazy(
                                                        'admin:user_reset_qr', kwargs={'pk': obj.pk}),
                                                    button_class='fa-qrcode text-warning',
                                                    button_popup="Reset User QR-Code",
                                                    button_active=self.request.user.has_perm(
                                                        'administration.p_staff_user_reset_qr'),
                                                    button_modal=True,
                                                    modal_validation=True)
        row['actions'] += reset_qr_btn

        reset_pw_btn = get_datatable_actions_button(button_text='',
                                                    button_url=reverse_lazy(
                                                        'admin:user_request_password_reset', kwargs={'pk': obj.pk}),
                                                    button_class='fa-unlock-alt text-warning',
                                                    button_popup="Send password reset URL",
                                                    button_active=self.request.user.has_perm(
                                                        'administration.p_staff_user_edit'),
                                                    button_modal=True,
                                                    modal_validation=True)

        row['actions'] += reset_pw_btn

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:user_delete', kwargs={'pk': obj.pk}),
                                                  button_class='fa-user-minus text-danger',
                                                  button_popup="Delete User",
                                                  button_active=self.request.user.has_perm(
                                                      'administration.p_staff_user_delete'),
                                                  button_modal=True,
                                                  modal_validation=False)
        row['actions'] += delete_btn


class UsersAndRolesView(AdminPermissionsMixin, TemplateView):
    template_name = 'users_and_roles.html'
    permission_required = ['administration.p_view']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Users & Roles',
            'page_id': 'users_and_roles',
        }

        context['metacontext'] = metacontext
        return context


class StaffUserPermissionsListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = Permission
    permission_required = ['core.x_super_admin']
    search_values_separator = '+'
    length_menu = [[150, 250, -1], [150, 250, 'all']]

    def get_initial_queryset(self, request=None):
        user = User.objects.get(pk=self.kwargs['pk'])
        qs = Permission.objects.prefetch_related('content_type').filter(
            codename__startswith='p_',
        ).annotate(
            perms_count=Count('user', filter=Q(user=user)),
            perm_granted=Case(
                When(perms_count__gte=1, then=True),
                default=False,
                output_field=BooleanField()
            ),
        )
        return qs

    column_defs = [
        {'name': 'pk', 'visible': False, 'searchable': False, 'orderable': True, },
        {'name': 'id', 'visible': True, 'searchable': False, 'orderable': True, },
        {'name': 'codename', 'visible': True, },
        {'name': 'name', 'visible': True, },
        {'name': 'perm_granted', 'title': 'Granted', 'placeholder': True,
         'searchable': True, 'orderable': False, 'boolean': True, 'choices': ((True, 'Yes'), (False, 'No'))},
    ]

    def customize_row(self, row, obj):
        user_id = self.kwargs['pk']

        if obj.perm_granted:
            perm_granted = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:staff_user_update_permission',
                                                            kwargs={'user_id': user_id, 'permission_id': obj.pk, }),
                                                        button_class='fa-check-circle text-success grant_perms_button',
                                                        button_active=self.request.user.has_perm('core.delete_comment'),
                                                        button_modal=False)
        else:
            perm_granted = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:staff_user_update_permission',
                                                            kwargs={'user_id': user_id, 'permission_id': obj.pk, }),
                                                        button_class='fa-ban text-danger grant_perms_button',
                                                        button_active=self.request.user.has_perm('core.delete_comment'),
                                                        button_modal=False)

        row['perm_granted'] = perm_granted
        return


class StaffUserPermissionsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.x_super_admin']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(pk=self.kwargs['pk'])
        person = getattr(user, 'person')

        metacontext = {
            'title': f'{person.fullname} - Role Permissions',
            'page_id': 'role_permissions_list',
            'datatable_uri': 'admin:staff_user_permissions_ajax',
            'datatable_uri_pk': user.pk,
        }

        context['metacontext'] = metacontext
        return context


class StaffUserPermissionsUpdateView(AdminPermissionsMixin, FormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['core.x_super_admin']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_valid(self, form, *args, **kwargs):
        user = User.objects.get(pk=self.kwargs['user_id'])
        permission = Permission.objects.get(pk=self.kwargs['permission_id'])

        if user.user_permissions.filter(pk=permission.id).exists():
            user.user_permissions.remove(permission)

        elif not user.user_permissions.filter(pk=permission.id).exists():
            user.user_permissions.add(permission)

        return super().form_valid(form)


class StaffUserInviteUpdateView(AdminPermissionsMixin, TemplateView):
    template_name = 'staff_user_invite_modal.html'

    user_id = None
    user = None
    person = None
    person_details = None
    person_position = None
    is_invitation = False

    def has_permission(self):
        return any([
            self.request.user.has_perm('administration.p_staff_user_invite'),
            self.request.user.has_perm('administration.p_staff_user_edit'),
        ])

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Get User instance from database
        self.user_id = self.kwargs.get('pk')
        if self.user_id:
            self.user = get_object_or_404(User, pk=self.user_id)
        else:
            self.is_invitation = True  # Variable signalise that we're creating new user
            self.user = User(is_staff=True)

        self.person = getattr(self.user, 'person', Person())
        self.person_details = getattr(self.person, 'details', PersonDetails())

        # Find existing position or create instance of new one
        person_position_qs = OrganisationPeople.objects.filter(
            person=self.person,
            organisation_id=100000000,
        )
        if person_position_qs.exists():
            self.person_position = person_position_qs.first()
        else:
            self.person_position = OrganisationPeople(role_id=14, organisation_id=100000000)

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_metacontext(self):
        if not self.user_id:
            metacontext = {
                'title': 'Invite AML Staff User',
                'action_button_class': 'btn-success',
                'action_button_text': 'Invite',
            }
        else:
            metacontext = {
                'title': 'Edit AML Staff User',
                'action_button_class': 'btn-success',
                'action_button_text': 'Update',
            }
        return metacontext

    def get(self, request, *args, **kwargs):
        return self.render_to_response({
            'user': self.user,
            'metacontext': self.get_metacontext(),
            'user_form': StaffUserForm(
                instance=self.user,
                prefix='user_form_pre'),
            'person_details_form': StaffPersonDetailsForm(
                instance=self.person_details,
                prefix='person_details_form_pre'),
            'person_position_form': StaffPersonPositionForm(
                instance=self.person_position,
                prefix='person_position_form_pre'),
        })

    def post(self, request, *args, **kwargs):
        request_user = getattr(self.request.user, 'person')
        user_form = StaffUserForm(request.POST or None,
                                  instance=self.user,
                                  prefix='user_form_pre')
        person_details_form = StaffPersonDetailsForm(request.POST or None,
                                                     instance=self.person_details,
                                                     prefix='person_details_form_pre')
        person_position_form = StaffPersonPositionForm(request.POST or None,
                                                       instance=self.person_position,
                                                       prefix='person_position_form_pre')

        # Process only if ALL forms are valid
        if all([
            user_form.is_valid(),
            person_details_form.is_valid(),
            person_position_form.is_valid(),
        ]):
            if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':

                self.person = person_details_form.save()
                # Save User instance
                user = user_form.save(commit=False)
                user.person = self.person
                user.save()
                user_form.save_m2m()

                # Save Person Position instance
                person_position = person_position_form.save(commit=False)
                person_position.person = self.person
                if self.is_invitation:
                    person_position.contact_email = self.person.details.contact_email
                    person_position.contact_phone = self.person.details.contact_phone
                person_position.save()

                if self.is_invitation:
                    from user.utils.user_invitations import invite_external_user
                    invite_external_user(user)
                    self.person.activity_log.create(
                        author=request_user,
                        record_slug='ops_portal_invitation',
                        details='Has been invited to AML Ops Portal',
                    )

                if not self.user_id:
                    messages.success(self.request, f'User invite sent successfully')

            return HttpResponseRedirect(self.get_success_url())
        else:
            if settings.DEBUG:
                print(
                    user_form.errors if user_form else '',
                    person_details_form.errors if person_details_form else '',
                    person_position_form.errors if person_position_form else '',
                )
            # Render forms with errors
            return self.render_to_response({
                'user': self.user,
                'metacontext': self.get_metacontext(),
                'user_form': user_form,
                'person_details_form': person_details_form,
                'person_position_form': person_position_form,
            })


class UserResetTOTPView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    model = User
    success_url = reverse_lazy('admin:staff_users_and_roles')
    permission_required = ['administration.p_staff_user_reset_qr']

    def form_valid(self, form, *args, **kwargs):
        user = self.model.objects.filter(pk=self.kwargs['pk']).first()

        user.totpdevice_set.all().delete()

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.model.objects.filter(pk=self.kwargs['pk']).first()

        if user.totpdevice_set.exists():
            metacontext = {
                'title': 'Reset User QR-code',
                'icon': 'fa-qrcode',
                'text': f'Are you sure about reset {user} QR-code?',
                'action_button_text': 'Reset',
                'action_button_class': 'btn-danger',
            }
        else:
            metacontext = {
                'title': 'Reset User QR-code',
                'icon': 'fa-qrcode',
                'text': f'User {user} does not have QR-code established',
                'action_button_text': 'Back',
                'action_button_class': 'd-none',
            }

        context['metacontext'] = metacontext
        return context


class UserSuspendView(AdminPermissionsMixin, BSModalFormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    model = User
    success_url = reverse_lazy('admin:staff_users_and_roles')
    permission_required = ['administration.p_staff_user_suspend']

    def form_valid(self, form, *args, **kwargs):

        def ignored_switch(object_to_update):
            return not object_to_update.is_active

        # Switch value
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            obj = self.model.objects.filter(pk=self.kwargs['pk']).first()
            obj.is_active = ignored_switch(obj)
            obj.save()

            if obj.is_active:
                messages.success(self.request, f'User {obj} activated')
            else:
                messages.warning(self.request, f'User {obj} suspended')

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        if not user.is_active:
            metacontext = {
                'title': 'Activate User',
                'icon': 'fa-user-check',
                'text': f'Are you sure about activate {user}',
                'action_button_text': 'Activate',
                'action_button_class': 'btn-success',
            }
        else:
            metacontext = {
                'title': 'Suspend User',
                'icon': 'fa-user-lock',
                'text': f'Are you sure about suspend {user}',
                'action_button_text': 'Suspend',
                'action_button_class': 'btn-danger',
            }

        context['metacontext'] = metacontext
        return context


class UserDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = User
    form_class = ConfirmationForm
    success_message = 'User successfully deleted'
    success_url = reverse_lazy('admin:staff_users_and_roles')
    permission_required = ['administration.p_staff_user_delete']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.model.objects.get(pk=self.kwargs['pk'])
        metacontext = {
            'title': 'Delete Staff User',
            'text': f'Are you sure about delete {obj}',
            'icon': 'fa-user-minus',
            'action_button_text': 'Delete',
            'action_button_class': 'btn-danger',
        }

        context['metacontext'] = metacontext
        return context
