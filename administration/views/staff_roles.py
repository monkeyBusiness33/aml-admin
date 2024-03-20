from bootstrap_modal_forms.generic import BSModalCreateView, BSModalDeleteView, BSModalUpdateView
from django.contrib.auth.models import Permission
from django.db.models import Case, When, BooleanField, Count, Q
from django.views.generic import TemplateView, FormView

from administration.forms.users_and_roles import StaffRoleForm
from core.forms import ConfirmationForm
from core.mixins import CustomAjaxDatatableView
from core.utils.datatables_functions import get_datatable_actions_button
from user.mixins import AdminPermissionsMixin
from django.urls import reverse_lazy

from user.models import Role


class StaffRolesListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = Role
    permission_required = ['administration.p_view']
    search_values_separator = '+'
    length_menu = [[10, 50, 100, 250, -1], [10, 50, 100, 250, 'all']]

    column_defs = [
        {'name': 'pk', 'title': 'ID', 'visible': False, 'searchable': False, 'orderable': True, 'width': 30, },
        {'name': 'name', 'visible': True, },
        {'name': 'description', 'visible': True, },
        {'name': 'actions', 'title': 'Actions', 'placeholder': True, 'searchable': False, 'orderable': False, },
    ]

    def customize_row(self, row, obj):
        row['actions'] = ''
        edit_btn = get_datatable_actions_button(button_text='',
                                                button_url=reverse_lazy(
                                                    'admin:users_roles_edit', kwargs={'pk': obj.pk}),
                                                button_class='fa-edit',
                                                button_active=self.request.user.has_perm(
                                                    'administration.p_staff_role_edit'),
                                                button_modal=True,
                                                modal_validation=True)
        row['actions'] += edit_btn

        perms_btn = get_datatable_actions_button(button_text='',
                                                 button_url=reverse_lazy(
                                                     'admin:staff_role_permissions', kwargs={'pk': obj.pk}),
                                                 button_class='fa-cogs',
                                                 button_active=self.request.user.has_perm('core.x_super_admin'),
                                                 button_modal=False)
        row['actions'] += perms_btn

        delete_btn = get_datatable_actions_button(button_text='',
                                                  button_url=reverse_lazy(
                                                      'admin:staff_role_delete', kwargs={'pk': obj.pk}),
                                                  button_class='fa-trash text-danger',
                                                  button_active=self.request.user.has_perm('core.x_super_admin'),
                                                  button_modal=True,
                                                  modal_validation=False)

        row['actions'] += delete_btn


class StaffRolePermissionsListAjaxView(AdminPermissionsMixin, CustomAjaxDatatableView):
    model = Permission
    permission_required = ['core.x_super_admin']
    search_values_separator = '+'
    length_menu = [[150, 250, -1], [150, 250, 'all']]

    def get_initial_queryset(self, request=None):
        role = Role.objects.get(pk=self.kwargs['pk'])
        qs = Permission.objects.prefetch_related('content_type').filter(
            codename__startswith='p_',
        ).annotate(
            perms_count=Count('roles', filter=Q(roles=role)),
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
        role_id = self.kwargs['pk']

        if obj.perm_granted:
            perm_granted = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:staff_role_update_permission',
                                                            kwargs={'role_id': role_id, 'permission_id': obj.pk, }),
                                                        button_class='fa-check-circle text-success grant_perms_button',
                                                        button_active=self.request.user.has_perm('core.delete_comment'),
                                                        button_modal=False)
        else:
            perm_granted = get_datatable_actions_button(button_text='',
                                                        button_url=reverse_lazy(
                                                            'admin:staff_role_update_permission',
                                                            kwargs={'role_id': role_id, 'permission_id': obj.pk, }),
                                                        button_class='fa-ban text-danger grant_perms_button',
                                                        button_active=self.request.user.has_perm('core.delete_comment'),
                                                        button_modal=False)

        row['perm_granted'] = perm_granted
        return


class StaffRolePermissionsListView(AdminPermissionsMixin, TemplateView):
    template_name = 'shared/ajax_datatable_page.html'
    permission_required = ['core.x_super_admin']

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        role = Role.objects.get(pk=self.kwargs['pk'])

        metacontext = {
            'title': f'{role.name} - Role Permissions',
            'page_id': 'role_permissions_list',
            'datatable_uri': 'admin:staff_role_permissions_ajax',
            'datatable_uri_pk': role.pk,
        }

        context['metacontext'] = metacontext
        return context


class StaffRolePermissionsUpdateView(AdminPermissionsMixin, FormView):
    template_name = 'includes/_modal_form.html'
    form_class = ConfirmationForm
    permission_required = ['core.x_super_admin']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def form_valid(self, form, *args, **kwargs):
        role = Role.objects.get(pk=self.kwargs['role_id'])
        permission = Permission.objects.get(pk=self.kwargs['permission_id'])

        if role.permissions.filter(pk=permission.id).exists():
            role.permissions.remove(permission)

        elif not role.permissions.filter(pk=permission.id).exists():
            role.permissions.add(permission)

        return super().form_valid(form)


class AdminUserRoleCreateView(AdminPermissionsMixin, BSModalCreateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = Role
    form_class = StaffRoleForm
    success_message = 'Staff role created successfully'
    permission_required = ['administration.p_staff_role_create']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Create Staff Role',
            'icon': 'fa-users',
        }

        context['metacontext'] = metacontext
        return context


class AdminUserRoleEditView(AdminPermissionsMixin, BSModalUpdateView):
    error_css_class = 'is-invalid'
    template_name = 'includes/_modal_form.html'
    model = Role
    form_class = StaffRoleForm
    success_message = 'Staff role updated successfully'
    permission_required = ['administration.p_staff_role_edit']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        metacontext = {
            'title': 'Edit Staff Role',
            'icon': 'fa-users',
        }

        context['metacontext'] = metacontext
        return context


class StaffUserRoleDeleteView(AdminPermissionsMixin, BSModalDeleteView):
    template_name = 'includes/_modal_form.html'
    model = Role
    form_class = ConfirmationForm
    success_message = 'Staff role deleted successfully'
    permission_required = ['core.x_super_admin']

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.get_object()

        metacontext = {
            'icon': 'fa-trash',
            'title': 'Delete Staff Role',
            'text': f'Please confirm deletion of the staff role "{role}"',
            'action_button_text': 'Confirm',
        }

        context['metacontext'] = metacontext
        return context
