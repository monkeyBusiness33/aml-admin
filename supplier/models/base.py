from core.models.settings import GlobalConfiguration


class Permissions(GlobalConfiguration):

    class Meta:
        proxy = True

        # The suppliers section is now just a list of companies, so keeping
        # this to the minimum for now.
        permissions = [
            ('p_view', 'Suppliers: view'),
            ('p_create', 'Suppliers: create'),
            ('p_update', 'Suppliers: update'),
        ]
