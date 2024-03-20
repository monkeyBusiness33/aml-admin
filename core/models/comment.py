from django.db import models
from django.utils.translation import gettext_lazy as _


class Comment(models.Model):
    text = models.CharField(_("Comment Text"), max_length=500)
    is_pinned = models.BooleanField(_("Pinned"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now=False, auto_now_add=True)
    author = models.ForeignKey("user.Person", verbose_name=_("Author"),
                               related_name='authored_comments',
                               on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", null=True,
                               related_name='comments',
                               on_delete=models.CASCADE)
    organisation = models.ForeignKey("organisation.Organisation", null=True,
                                     related_name='comments',
                                     on_delete=models.CASCADE)
    handling_service = models.ForeignKey("handling.HandlingService", null=True,
                                         related_name='comments',
                                         on_delete=models.CASCADE)
    supplier_fuel_agreement = models.ForeignKey("supplier.FuelAgreement", null=True,
                                                related_name='comments',
                                                on_delete=models.CASCADE)
    handling_request = models.ForeignKey("handling.HandlingRequest", verbose_name=_("Handling Request"),
                                         null=True,
                                         related_name='comments',
                                         on_delete=models.CASCADE)
    mission = models.ForeignKey("mission.Mission", verbose_name=_("Mission"),
                                null=True,
                                related_name='comments',
                                on_delete=models.CASCADE)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        db_table = 'comments'

    def __str__(self):
        return f'{self.pk}'

    @property
    def is_read(self):
        """
        The read_statuses queryset is already prefiltered using prefetch_related
        in the get_queryset method of the view, so we only get the statuses
        relevant to the person tied to the HTTP request.
        We return the value of is_read if available and True by default
        (if the comment is older than the functionality or user did not exist at the time of its creation)
        """
        if not self.read_statuses.count():
            return True

        status = self.read_statuses.last()

        return status.is_read

    def can_be_removed_by(self, user):
        author_user = getattr(self.author, 'user', None)
        if user == author_user:
            return True
        if user.has_perm('core.p_comments_moderate'):
            return True


class CommentReadStatus(models.Model):
    comment = models.ForeignKey("Comment", verbose_name=_("Comment"),
                                related_name='read_statuses', on_delete=models.CASCADE)
    person = models.ForeignKey("user.Person", verbose_name=_("Person"),
                               related_name='comments_read_statuses', on_delete=models.CASCADE)
    is_read = models.BooleanField(_("Is Read?"), default=False)

    class Meta:
        db_table = 'comments_read_tracking'
