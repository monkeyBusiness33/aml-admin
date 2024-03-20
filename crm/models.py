from django.db import models
from django.utils.translation import gettext_lazy as _
from app.storage_backends import OrganisationPeopleActivityStorage


class Activity(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    icon = models.CharField(_("Icon"), max_length=10)
    
    class Meta:
        db_table = 'crm_activities'

    def __str__(self):
        return self.name


class OrganisationPeopleActivity(models.Model):
    organisation = models.ForeignKey("organisation.Organisation",
                                     verbose_name=_("Organisation"),
                                     null=True,
                                     related_name='crm_activity_log',
                                     on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               null=True,
                               related_name='crm_activity_log',
                               on_delete=models.CASCADE)
    crm_activity = models.ForeignKey("crm.Activity", verbose_name=_("Activity"), on_delete=models.CASCADE)
    datetime = models.DateTimeField(_("Date & Time"), auto_now=False, auto_now_add=False)
    description = models.CharField(_("Description"), max_length=500, null=True)
    is_pinned = models.BooleanField(_("Pinned?"), default=False)
    # opportunity = models.ForeignKey("app.Model", verbose_name=_(""), on_delete=models.CASCADE)
    created_by = models.ForeignKey("user.Person", verbose_name=_("Recorded By"),
                                   related_name='authored_crm_activities',
                                   on_delete=models.CASCADE)

    class Meta:
        db_table = 'organisations_people_activities'

    def __str__(self):
        return f'{self.pk}'


class OrganisationPeopleActivityAttachment(models.Model):
    activity = models.ForeignKey("crm.OrganisationPeopleActivity",
                                 verbose_name=_("Activity"), 
                                 related_name='attachments',
                                 on_delete=models.CASCADE)
    description = models.CharField(_("Description"), max_length=100)
    file = models.FileField(_("Attachment"), storage=OrganisationPeopleActivityStorage())

    class Meta:
        db_table = 'organisations_people_activities_attachments'

    def __str__(self):
        return f'{self.activity.crm_activity.name}'
