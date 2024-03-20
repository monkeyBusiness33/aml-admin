from datetime import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _


class ArchivableModelManager(models.Manager):
    """
    A manager that filters out archived instances by default, and
    adds method to access them explicitly.
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def archived_only(self):
        return super().get_queryset().filter(deleted_at__isnull=False)

    def with_archived(self):
        return super().get_queryset()


class ArchivableModelQuerySet(models.QuerySet):
    """
    A queryset for 'archivable' models, this is only needed when queryset
    is used to create a manager directly using `as_manager`.
    """
    def as_manager(cls):
        manager = ArchivableModelManager.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager

    as_manager.queryset_only = True
    as_manager = classmethod(as_manager)


class ArchivableModel(models.Model):
    """
    An abstract base class for models that need to be archived for track-keeping
    but removed from day-to-day use, effectively a soft deletion.
    (Requires migrating to add the `deleted_at` column)
    """
    deleted_at = models.DateTimeField(_("Deleted At"), auto_now=False, auto_now_add=False, null=True, blank=True)

    objects = ArchivableModelManager()

    def archive(self):
        self.deleted_at = datetime.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()

    class Meta:
        abstract = True
