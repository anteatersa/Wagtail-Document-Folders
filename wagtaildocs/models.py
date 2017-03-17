from __future__ import absolute_import, unicode_literals

import os.path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import Signal
from django.dispatch.dispatcher import receiver
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from taggit.managers import TaggableManager

from wagtail.wagtailadmin.utils import get_object_usage
from wagtail.wagtailcore.models import CollectionMember
from wagtail.wagtailsearch import index
from wagtail.wagtailsearch.queryset import SearchableQuerySetMixin


class DocumentQuerySet(SearchableQuerySetMixin, models.QuerySet):
    pass


class DocumentFolder(models.Model):
    folder = models.ForeignKey('self', null=True)   # Null value would mean it was in root image folder
    title = models.CharField(max_length=255, verbose_name=_('title'))
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True, db_index=True)

    admin_form_fields = (
        'title',
    )

    def get_parent(self):
        if self.folder:
            return self.folder
        else:
            return False

    def get_breadcrumbs(self):
        folder_breadcrumb = []
        folder_breadcrumb_current_folder = self
        while folder_breadcrumb_current_folder:
            folder_breadcrumb.append(folder_breadcrumb_current_folder)
            folder_breadcrumb_current_folder = folder_breadcrumb_current_folder.get_parent()
        folder_breadcrumb.reverse()
        return folder_breadcrumb

    def get_subfolders(self):
        return DocumentFolder.objects.filter(folder = self)


def get_folder_model():
    return DocumentFolder


@python_2_unicode_compatible
class AbstractDocument(CollectionMember, index.Indexed, models.Model):
    folder = models.ForeignKey(DocumentFolder, null = True, blank = True) # Null value would be root document folder
    title = models.CharField(max_length=255, verbose_name=_('title'))
    file = models.FileField(upload_to='documents', verbose_name=_('file'))
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True)
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('uploaded by user'),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL
    )

    tags = TaggableManager(help_text=None, blank=True, verbose_name=_('tags'))

    objects = DocumentQuerySet.as_manager()

    search_fields = CollectionMember.search_fields + [
        index.SearchField('title', partial_match=True, boost=10),
        index.RelatedFields('tags', [
            index.SearchField('name', partial_match=True, boost=10),
        ]),
        index.FilterField('uploaded_by_user'),
    ]

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def file_extension(self):
        return os.path.splitext(self.filename)[1][1:]

    @property
    def url(self):
        return reverse('wagtaildocs_serve', args=[self.id, self.filename])

    def get_usage(self):
        return get_object_usage(self)

    @property
    def usage_url(self):
        return reverse('wagtaildocs:document_usage',
                       args=(self.id,))

    def is_editable_by_user(self, user):
        from wagtail.wagtaildocs.permissions import permission_policy
        return permission_policy.user_has_permission_for_instance(user, 'change', self)

    class Meta:
        abstract = True
        verbose_name = _('document')


class Document(AbstractDocument):
    admin_form_fields = (
        'folder',
        'title',
        'file',
        'collection',
        'tags'
    )


def get_document_model():
    from django.conf import settings
    from django.apps import apps

    try:
        app_label, model_name = settings.WAGTAILDOCS_DOCUMENT_MODEL.split('.')
    except AttributeError:
        return Document
    except ValueError:
        raise ImproperlyConfigured("WAGTAILDOCS_DOCUMENT_MODEL must be of the form 'app_label.model_name'")

    document_model = apps.get_model(app_label, model_name)
    if document_model is None:
        raise ImproperlyConfigured(
            "WAGTAILDOCS_DOCUMENT_MODEL refers to model '%s' that has not been installed" %
            settings.WAGTAILDOCS_DOCUMENT_MODEL
        )
    return document_model


# Receive the post_delete signal and delete the file associated with the model instance.
@receiver(post_delete, sender=Document)
def document_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.file.delete(False)


document_served = Signal(providing_args=['request'])
