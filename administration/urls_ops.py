from django.urls import path

from administration.views.broadcast_message import BroadcastMessageActivityLogAjaxView, SendBroadcastMessageView
from administration.views.email_distribution_control import EmailDistributionControlView, \
    EmailDistributionControlAddressesAjaxView, EmailDistributionControlAddressCreateUpdateView, \
    EmailDistributionControlAddressDeleteView, EmailDistributionControlSpecificRecipientRulesAjaxView, \
    EmailDistributionControlRuleCreateUpdateView, EmailDistributionControlRuleDeleteView
from administration.views.staff_roles import StaffRolesListAjaxView, StaffRolePermissionsListAjaxView, \
    StaffRolePermissionsListView, StaffRolePermissionsUpdateView, StaffUserRoleDeleteView, AdminUserRoleCreateView, \
    AdminUserRoleEditView
from administration.views.staff_users import UsersAndRolesView, StaffUsersListAjaxView, StaffUserInviteUpdateView, \
    UserSuspendView, UserDeleteView, UserResetTOTPView, StaffUserPermissionsListAjaxView, StaffUserPermissionsListView, \
    StaffUserPermissionsUpdateView

urlpatterns = [
    # Broadcast message
    path('send_broadcast_message/activity_log_ajax/',
         BroadcastMessageActivityLogAjaxView.as_view(),
         name='broadcast_message_activity_log'),
    path('send_broadcast_message/', SendBroadcastMessageView.as_view(), name='send_broadcast_message'),

    # Email Distribution Control
    path('email_distribution_control/', EmailDistributionControlView.as_view(), name='email_distribution_control'),

    path('email_distribution_control/addresses/create/', EmailDistributionControlAddressCreateUpdateView.as_view(),
         name='email_distribution_control_addresses_create'),
    path('email_distribution_control/addresses/<int:pk>/edit/',
         EmailDistributionControlAddressCreateUpdateView.as_view(),
         name='email_distribution_control_addresses_edit'),
    path('email_distribution_control/addresses/<int:pk>/delete/',
         EmailDistributionControlAddressDeleteView.as_view(),
         name='email_distribution_control_addresses_delete'),
    path('email_distribution_control/addresses_ajax/', EmailDistributionControlAddressesAjaxView.as_view(),
         name='email_distribution_control_addresses_ajax'),

    path('email_distribution_control/specific_recipients_rules_ajax/<str:rule_target>/',
         EmailDistributionControlSpecificRecipientRulesAjaxView.as_view(),
         name='email_distribution_control_specific_recipients_rules_ajax'),
    path('email_distribution_control/rules/<str:rule_target>/create/',
         EmailDistributionControlRuleCreateUpdateView.as_view(),
         name='email_distribution_control_rule_create'),
    path('email_distribution_control/rules/<int:pk>/edit/',
         EmailDistributionControlRuleCreateUpdateView.as_view(),
         name='email_distribution_control_rule_edit'),
    path('email_distribution_control/rules/<int:pk>/delete/',
         EmailDistributionControlRuleDeleteView.as_view(),
         name='email_distribution_control_rule_delete'),

    # Users Section
    path('users_and_roles/', UsersAndRolesView.as_view(), name='staff_users_and_roles'),
    path('users_ajax/', StaffUsersListAjaxView.as_view(), name='staff_users_ajax'),
    path('users/invite/', StaffUserInviteUpdateView.as_view(), name='staff_user_invite'),
    path('users/<int:pk>/update/', StaffUserInviteUpdateView.as_view(), name='staff_user_update'),
    path('users/<int:pk>/permissions_ajax/', StaffUserPermissionsListAjaxView.as_view(),
         name='staff_user_permissions_ajax'),
    path('users/<int:pk>/permissions/', StaffUserPermissionsListView.as_view(), name='staff_user_permissions'),
    path('users/<int:user_id>/update_permission/<int:permission_id>/', StaffUserPermissionsUpdateView.as_view(),
         name='staff_user_update_permission'),


    path('roles_ajax/', StaffRolesListAjaxView.as_view(), name='staff_roles_ajax'),
    path('role/<int:pk>/permissions_ajax/', StaffRolePermissionsListAjaxView.as_view(),
         name='staff_role_permissions_ajax'),

    path('role/<int:pk>/permissions/', StaffRolePermissionsListView.as_view(), name='staff_role_permissions'),
    path('role/<int:role_id>/update_permission/<int:permission_id>/', StaffRolePermissionsUpdateView.as_view(),
         name='staff_role_update_permission'),

    path('role/<int:pk>/', StaffUserRoleDeleteView.as_view(), name='staff_role_delete'),

    path('users/suspend/<int:pk>/', UserSuspendView.as_view(), name='user_suspend'),
    path('users/delete/<int:pk>/', UserDeleteView.as_view(), name='user_delete'),
    path('users/reset-qr/<int:pk>/', UserResetTOTPView.as_view(), name='user_reset_qr'),
    path('users/roles/add', AdminUserRoleCreateView.as_view(), name='users_roles_add'),
    path('users/roles/edit/<int:pk>/', AdminUserRoleEditView.as_view(), name='users_roles_edit'),
    path('users/aircraft_types/<int:pk>/', AdminUserRoleEditView.as_view(), name='user_aircraft_types'),
]
