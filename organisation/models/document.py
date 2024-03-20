from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from app.storage_backends import OrganisationDocumentStorage


class OrganisationDocumentTypeQuerySet(models.QuerySet):
    def applicable_to_org(self, organisation):
        # Apply main org. type
        type_query = (Q(organisation_type=organisation.details.type)
                      | Q(organisation_type__isnull=True))

        # Apply secondary types
        if hasattr(organisation, 'operator_details'):
            type_query |= Q(organisation_type=1)
        if hasattr(organisation, 'handler_details'):
            type_query |= Q(organisation_type=3)
        if bool(organisation.sells_fuel):
            type_query |= Q(organisation_type=2)
        if hasattr(organisation, 'ipa_details'):
            type_query |= Q(organisation_type=4)
        if hasattr(organisation, 'oilco_details'):
            type_query |= Q(organisation_type=5)
        if hasattr(organisation, 'dao_details'):
            type_query |= Q(organisation_type=1001)
        if hasattr(organisation, 'nasdl_details'):
            type_query |= Q(organisation_type=1002)
        if bool(organisation.provides_services):
            type_query |= Q(organisation_type=14)
        if bool(organisation.provides_trip_support):
            type_query |= Q(organisation_type=11)

        return self.filter(type_query)


class OrganisationDocumentType(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    organisation_type = models.ForeignKey("organisation.OrganisationType",
                                          verbose_name=_("Organisation Type"),
                                          null=True, blank=True,
                                          on_delete=models.CASCADE)

    objects = OrganisationDocumentTypeQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        db_table = 'organisations_documents_types'

    def __str__(self):
        return self.name


class OrganisationDocument(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Organisation"),
                                     related_name='documents',
                                     on_delete=models.CASCADE)
    name = models.CharField(_("Name"), max_length=100)
    description = models.CharField(_("Description"), max_length=500,
                                   null=True, blank=True)
    type = models.ForeignKey("organisation.OrganisationDocumentType",
                             verbose_name=_("Document Type"),
                             on_delete=models.CASCADE)
    file = models.FileField(_("Document File"),
                            storage=OrganisationDocumentStorage())

    class Meta:
        db_table = 'organisations_documents'

    def __str__(self):
        return self.name
