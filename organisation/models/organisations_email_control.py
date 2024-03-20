from django.db import models
from django.db.models import QuerySet, Q
from django.utils.translation import gettext_lazy as _


class EmailFunction(models.Model):
    name = models.CharField(_("Name"), max_length=255, default='')
    codename = models.SlugField(_("Code Name"), max_length=255, unique=True)

    class Meta:
        db_table = 'organisations_email_control_functions'

    def __str__(self):
        return f'{self.name}'

    def get_addresses_cc(self, recipient):  # noqa
        result = []
        addresses = OrganisationEmailControlAddress.objects.get_addresses_cc(recipient=recipient, email_function=self)
        for address in addresses:
            result += address.get_email_address()
        return result

    def get_addresses_bcc(self, recipient):  # noqa
        result = []
        addresses = OrganisationEmailControlAddress.objects.get_addresses_bcc(recipient=recipient, email_function=self)
        for address in addresses:
            result += address.get_email_address()
        return result


class OrganisationEmailControlAddressQuerySet(QuerySet):
    def get_for_recipient(self, recipient):
        qs = self.filter(
            Q(email_control_rules__recipient_organisation=recipient) |
            Q(email_control_rules__recipient_based_airport__in=recipient.based_airports) |
            Q(email_control_rules__recipient_based_country=recipient.details.country)
        ).distinct()
        return qs

    def get_addresses_cc(self, recipient, email_function):
        return self.get_for_recipient(recipient=recipient).filter(
            email_control_rules__is_cc=True,
            email_control_rules__email_function=email_function,
        )

    def get_addresses_bcc(self, recipient, email_function):
        return self.get_for_recipient(recipient=recipient).filter(
            email_control_rules__is_bcc=True,
            email_control_rules__email_function=email_function,
        )


class OrganisationEmailControlAddress(models.Model):
    email_address = models.EmailField(_("Email Address"), max_length=254, null=True, blank=True)
    label = models.CharField(_("Label"), max_length=200, null=True, blank=True)
    organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Organisation"),
                                     related_name='email_control_addresses',
                                     null=True, blank=True,
                                     on_delete=models.CASCADE)
    organisation_person = models.ForeignKey("organisation.OrganisationPeople", verbose_name=_("Person"),
                                            related_name='email_control_addresses',
                                            null=True, blank=True,
                                            on_delete=models.CASCADE)

    objects = OrganisationEmailControlAddressQuerySet().as_manager()

    class Meta:
        db_table = 'organisations_email_control_addresses'

    def __str__(self):
        return f'{self.label}'

    def get_email_address(self) -> list:
        if self.email_address:
            return [self.email_address]
        if self.organisation:
            return self.organisation.get_email_address()
        if self.organisation_person:
            if self.organisation_person.contact_email:
                return [self.organisation_person.contact_email]
        return []


class OrganisationEmailControlRule(models.Model):
    recipient_organisation = models.ForeignKey("organisation.Organisation", verbose_name=_("Recipient Organisation"),
                                               related_name='organisation_email_control_rules',
                                               null=True, blank=True,
                                               on_delete=models.CASCADE)
    recipient_based_airport = models.ForeignKey("organisation.Organisation", verbose_name=_("Recipient Based Airport"),
                                                related_name='airport_email_control_rules',
                                                limit_choices_to={'details__type_id': 8,
                                                                  'airport_details__isnull': False},
                                                null=True, blank=True,
                                                on_delete=models.CASCADE)
    recipient_based_country = models.ForeignKey("core.Country", verbose_name=_("Recipient Based Country"),
                                                related_name='country_email_control_rules',
                                                null=True, blank=True,
                                                on_delete=models.CASCADE)
    email_function = models.ForeignKey("organisation.EmailFunction", verbose_name=_("Email Function"),
                                       related_name='email_control_rules',
                                       on_delete=models.CASCADE)
    aml_email = models.ForeignKey("organisation.OrganisationEmailControlAddress", verbose_name=_("Address to Cc/Bcc"),
                                  related_name='email_control_rules',
                                  on_delete=models.CASCADE)
    is_cc = models.BooleanField(_("CC"), default=False)
    is_bcc = models.BooleanField(_("BCC"), default=False)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Created By"),
                                   related_name='email_control_rules',
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)

    class Meta:
        db_table = 'organisations_email_control_rules'

    def __str__(self):
        return f'{self.pk}'
