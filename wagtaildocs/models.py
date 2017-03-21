from __future__ import absolute_import, unicode_literals

import os
import shutil
import os.path
from unidecode import unidecode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
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

DOCUMENTS_FOLDER_NAME = 'documents'


def get_upload_to(instance, filename):
    """
    Obtain a valid upload path for the document.

    This needs to be a module-level function so that it can be referenced within migrations,
    but simply delegates to the `get_upload_to` method of the instance, so that AbstractDocument
    subclasses can override it.
    """
    return instance.get_upload_to(filename)


class DocumentQuerySet(SearchableQuerySetMixin, models.QuerySet):
    pass


class DocumentFolder(models.Model):
    folder = models.ForeignKey('self', null=True)   # Null value would mean it was in root image folder
    title = models.CharField(max_length=255, verbose_name=_('title'))
    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True, db_index=True)
    path = models.TextField(blank=True)

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
        return DocumentFolder.objects.filter(folder=self)

    def save(self, *args, **kwargs):
        # do a unidecode in the title and then
        # replace non-ascii characters in title with _ , to sidestep issues with filesystem encoding
        unicoded_title = "".join((i if ord(i) < 128 else '_') for i in unidecode(self.title))

        parent_folder = self.folder
        if parent_folder:
            self.path = os.path.join(parent_folder.path, unicoded_title)
        else:
            self.path = os.path.join(DOCUMENTS_FOLDER_NAME, unicoded_title)

        if self.pk is None:
            super(DocumentFolder, self).save()
            # Create the folder
            os.makedirs(self.get_complete_path())
        else:
            if 'rename' in kwargs and not kwargs['rename']:
                # In case of sub folders, only the DB needs to updated
                # The physical path would be updated by the parent folder
                super(DocumentFolder, self).save()
            else:
                current_path = DocumentFolder.objects.get(pk=self.pk).get_complete_path()
                super(DocumentFolder, self).save()
                # Rename the folder
                os.rename(current_path, self.get_complete_path())

            # Update the documents' paths
            Document = get_document_model()
            documents = Document.objects.filter(folder=self)
            for document in documents:
                document.file.name = os.path.join(self.path, document.filename)
                document.save()

            # Update the sub_folders' path
            for sub_folder in self.get_subfolders():
                sub_folder.save(rename=False)

    def delete(self, *args, **kwargs):
        # Recursively delete the sub folders
        for sub_folder in self.get_subfolders():
            sub_folder.delete()

        # Delete the documents
        Document = get_document_model()
        documents = Document.objects.filter(folder=self)
        for document in documents:
            document.delete()

        try:
            # Delete the physical folder
            shutil.rmtree(self.get_complete_path())
        except FileNotFoundError:
            pass

        super(DocumentFolder, self).delete()

    def validate_folder(self):
        """Validates whether a folder can be created.
        Performs two types of validation:
        1. Checks if a DB entry is present.
        2. Checks if a physical folder exists in the system."""

        unicoded_title = "".join((i if ord(i) < 128 else '_') for i in unidecode(self.title))
        parent_folder = self.folder

        if parent_folder:
            if DocumentFolder.objects.filter(folder=parent_folder, title=self.title).count() > 0:
                raise ValidationError("Folder exists in the DB!", code='db')
            folder_path = os.path.join(settings.MEDIA_ROOT, parent_folder.path, unicoded_title)
            if os.path.isdir(folder_path):
                raise ValidationError("Folder exists in the OS!", code='os')
        else:
            if DocumentFolder.objects.filter(folder__isnull=True, title=self.title).count() > 0:
                raise ValidationError("Folder exists in the DB!", code='db')
            folder_path = os.path.join(settings.MEDIA_ROOT, DOCUMENTS_FOLDER_NAME, unicoded_title)
            if os.path.isdir(folder_path):
                raise ValidationError("Folder exists in the OS!", code='os')

    def get_complete_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.path)

    def __str__(self):
        return self.title



def get_folder_model():
    return DocumentFolder


@python_2_unicode_compatible
class AbstractDocument(CollectionMember, index.Indexed, models.Model):
    folder = models.ForeignKey(DocumentFolder, null=True, blank=True)  # Null value would be root document folder
    title = models.CharField(max_length=255, verbose_name=_('title'))
    file = models.FileField(upload_to=get_upload_to, verbose_name=_('file'))
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

    def get_upload_to(self, filename):
        filename = self.file.field.storage.get_valid_name(filename)

        # do a unidecode in the filename and then
        # replace non-ascii characters in filename with _ , to sidestep issues with filesystem encoding
        filename = "".join((i if ord(i) < 128 else '_') for i in unidecode(filename))

        # Truncate filename so it fits in the 100 character limit
        # https://code.djangoproject.com/ticket/9893
        if self.folder:
            full_path = os.path.join(self.folder.path, filename)
        else:
            full_path = os.path.join(DOCUMENTS_FOLDER_NAME, filename)

        if len(full_path) >= 95:
            chars_to_trim = len(full_path) - 94
            prefix, extension = os.path.splitext(filename)
            filename = prefix[:-chars_to_trim] + extension
            if self.folder:
                full_path = os.path.join(self.folder.path, filename)
            else:
                full_path = os.path.join(DOCUMENTS_FOLDER_NAME, filename)
        return full_path

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
