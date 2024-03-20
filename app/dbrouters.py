

class CustomDBRouter(object):

    def db_for_read(self, model, **hints):  # noqa
        # if model._meta.app_label == 'aml_legacy':
        #     return 'aml_legacy'

        # database stickiness
        instance = hints.get('instance')
        if instance is not None and instance._state.db:
            return instance._state.db

        return 'default_replica'

    def db_for_write(self, model, **hints):  # noqa
        # if model._meta.app_label == 'aml_legacy':
        #     return 'aml_legacy'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):  # noqa
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        db_set = {'default', 'default_replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):  # noqa
        """
        Disable migrations for the ADS and legacy AML database
        """
        disable_migrations_for_databases = ['ads', ]
        if db in disable_migrations_for_databases:
            return False
        else:
            return None
