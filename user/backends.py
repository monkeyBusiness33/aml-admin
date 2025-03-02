from django.db.models import Exists, OuterRef, Q
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
UserModel = get_user_model()


class AMLBaseBackend:
    def authenticate(self, request, **kwargs):
        return None

    def get_user(self, user_id):
        return None

    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def get_roles_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        return {
            *self.get_user_permissions(user_obj, obj=obj),
            *self.get_roles_permissions(user_obj, obj=obj),
        }

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj=obj)


# class AMLBackend(AMLBaseBackend):
#     '''
#     User auth backend overwrite to able login using custom AML MD5 passwords hashing.
#     '''

#     def authenticate(self, request, username=None, password=None):
#         def _check_legacy_aml_password(user, password):

#             # Hash with salt (appuser passwords)
#             password_salt = '@#$!#'
#             username = user.username
#             salted_password = password_salt + username + password + password_salt
#             salted_hash = hashlib.md5(
#                 salted_password.encode('utf-8')).hexdigest()

#             # Hash without salt (clientuser passwords)
#             unsalted_hash = hashlib.md5(password.encode('utf-8')).hexdigest()

#             if user.password == salted_hash or user.password == unsalted_hash:
#                 return True

#         if username is None or password is None:
#             return
#         usermodel = get_user_model()

#         try:
#             user = usermodel._default_manager.get_by_natural_key(username)
#         except usermodel.DoesNotExist:
#             user = None
#         if user and _check_legacy_aml_password(user, password):
#             return user
#         return None

#     def get_user(self, user_id):
#         try:
#             return UserModel.objects.get(pk=user_id)
#         except UserModel.DoesNotExist:
#             return None

#     def _get_role_permissions(self, user_obj):
#         user_groups_field = get_user_model()._meta.get_field('staff_role')
#         user_groups_query = 'adminuserrole__%s' % user_groups_field.related_query_name()
#         return Permission.objects.filter(**{user_groups_query: user_obj})

#     def _get_permissions(self, user_obj, obj, from_name):
#         if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
#             return set()

#         perm_cache_name = '_%s_perm_cache' % from_name
#         if not hasattr(user_obj, perm_cache_name):
#             if user_obj.is_superuser:
#                 perms = Permission.objects.all()
#             else:
#                 perms = getattr(self, '_get_%s_permissions' %
#                                 from_name)(user_obj)
#             perms = perms.values_list(
#                 'content_type__app_label', 'codename').order_by()
#             setattr(user_obj, perm_cache_name, {
#                     "%s.%s" % (ct, name) for ct, name in perms})
#         return getattr(user_obj, perm_cache_name)

#     def get_role_permissions(self, user_obj, obj=None):
#         """
#         Return a set of permission strings the user `user_obj` has from the
#         groups they belong.
#         """
#         return self._get_permissions(user_obj, obj, 'role')

#     def get_all_permissions(self, user_obj, obj=None):
#         if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
#             return set()
#         if not hasattr(user_obj, '_perm_cache'):
#             user_obj._perm_cache = super().get_all_permissions(user_obj)
#         return user_obj._perm_cache

#     def has_perm(self, user_obj, perm, obj=None):
#         return user_obj.is_active and super().has_perm(user_obj, perm, obj=obj)

#     def has_module_perms(self, user_obj, app_label):
#         """
#         Return True if user_obj has any permissions in the given app_label.
#         """
#         return user_obj.is_active and any(
#             perm[:perm.index('.')] == app_label
#             for perm in self.get_all_permissions(user_obj)
#         )

#     def with_perm(self, perm, is_active=True, include_superusers=True, obj=None):
#         """
#         Return users that have permission "perm". By default, filter out
#         inactive users and include superusers.
#         """
#         if isinstance(perm, str):
#             try:
#                 app_label, codename = perm.split('.')
#             except ValueError:
#                 raise ValueError(
#                     'Permission name should be in the form '
#                     'app_label.permission_codename.'
#                 )
#         elif not isinstance(perm, Permission):
#             raise TypeError(
#                 'The `perm` argument must be a string or a permission instance.'
#             )

#         if obj is not None:
#             return UserModel._default_manager.none()

#         permission_q = Q(adminuserrole__users=OuterRef('pk'))
#         if isinstance(perm, Permission):
#             permission_q &= Q(pk=perm.pk)
#         else:
#             permission_q &= Q(codename=codename,
#                               content_type__app_label=app_label)

#         user_q = Exists(Permission.objects.filter(permission_q))
#         if include_superusers:
#             user_q |= Q(staff_role__id=1)
#         if is_active is not None:
#             user_q &= Q(is_active=is_active)

#         return UserModel._default_manager.filter(user_q)


class AMLUserBackend(AMLBaseBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    This class based on built-in Django's class ModelBackend with the following changes
    - User's 'group' renamed to the 'roles'
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def _get_user_permissions(self, user_obj):  # noqa
        return user_obj.user_permissions.all()

    def _get_roles_permissions(self, user_obj):  # noqa
        user_groups_field = get_user_model()._meta.get_field('roles')
        user_groups_query = 'roles__%s' % user_groups_field.related_query_name()
        return Permission.objects.filter(**{user_groups_query: user_obj})

    def _get_permissions(self, user_obj, obj, from_name):
        """
        Return the permissions of `user_obj` from `from_name`. `from_name` can
        be either "group" or "user" to return permissions from
        `_get_group_permissions` or `_get_user_permissions` respectively.
        """
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        perm_cache_name = '_%s_perm_cache' % from_name
        if not hasattr(user_obj, perm_cache_name):
            if user_obj.roles.filter(pk=1).cache(ops=['exists']).exists():
                perms = Permission.objects.all()
            else:
                perms = getattr(self, '_get_%s_permissions' % from_name)(user_obj)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            setattr(user_obj, perm_cache_name, {"%s.%s" % (ct, name) for ct, name in perms})
        return getattr(user_obj, perm_cache_name)

    def get_user_permissions(self, user_obj, obj=None):
        """
        Return a set of permission strings the user `user_obj` has from their
        `user_permissions`.
        """
        return self._get_permissions(user_obj, obj, 'user')

    def get_roles_permissions(self, user_obj, obj=None):
        """
        Return a set of permission strings the user `user_obj` has from the
        groups they belong.
        """
        return self._get_permissions(user_obj, obj, 'roles')

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = super().get_all_permissions(user_obj)
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        return user_obj.is_active and super().has_perm(user_obj, perm, obj=obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Return True if user_obj has any permissions in the given app_label.
        """
        return user_obj.is_active and any(
            perm[:perm.index('.')] == app_label
            for perm in self.get_all_permissions(user_obj)
        )

    def with_perm(self, perm, is_active=True, include_superusers=True, obj=None):
        """
        Return users that have permission "perm". By default, filter out
        inactive users and include superusers.
        """
        if isinstance(perm, str):
            try:
                app_label, codename = perm.split('.')
            except ValueError:
                raise ValueError(
                    'Permission name should be in the form '
                    'app_label.permission_codename.'
                )
        elif not isinstance(perm, Permission):
            raise TypeError(
                'The `perm` argument must be a string or a permission instance.'
            )

        if obj is not None:
            return UserModel._default_manager.none()

        permission_q = Q(roles__user=OuterRef('pk'))
        if isinstance(perm, Permission):
            permission_q &= Q(pk=perm.pk)
        else:
            permission_q &= Q(codename=codename, content_type__app_label=app_label)

        user_q = Exists(Permission.objects.filter(permission_q))
        if include_superusers:
            user_q |= Q(roles__id=1)
        if is_active is not None:
            user_q &= Q(is_active=is_active)

        return UserModel._default_manager.filter(user_q)

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
