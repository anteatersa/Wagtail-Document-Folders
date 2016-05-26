from django import forms
from django.forms.models import modelform_factory
from django.utils.translation import ugettext_lazy as _

from wagtail.wagtailadmin import widgets
from wagtail.wagtailadmin.forms import (
    BaseCollectionMemberForm, collection_member_permission_formset_factory
)
from wagtail.wagtaildocs.models import Document
from wagtail.wagtaildocs.permissions import permission_policy as documents_permission_policy


class BaseDocumentForm(BaseCollectionMemberForm):
    permission_policy = documents_permission_policy


def get_document_form(model):
    fields = model.admin_form_fields
    if 'collection' not in fields:
        # force addition of the 'collection' field, because leaving it out can
        # cause dubious results when multiple collections exist (e.g adding the
        # document to the root collection where the user may not have permission) -
        # and when only one collection exists, it will get hidden anyway.
        fields = list(fields) + ['collection']

    return modelform_factory(
        model,
        form=BaseDocumentForm,
        fields=fields,
        widgets={
            'folder': forms.HiddenInput(),
            'tags': widgets.AdminTagWidget,
            'file': forms.FileInput()
        })


def get_document_multi_form(model):
    return modelform_factory(
        model,
        form=BaseDocumentForm,
        fields=['title', 'collection', 'tags'],
        widgets={
            'folder': forms.HiddenInput(),
            'tags': widgets.AdminTagWidget,
            'file': forms.FileInput()
        })

class DocumentFolderForm(forms.ModelForm):
    title = forms.CharField(required=True)

def get_folder_form(model):
    fields = model.admin_form_fields

    return modelform_factory(
        model,
        form=DocumentFolderForm,
        fields=fields,
        #formfield_callback=formfield_for_dbfield,
        # set the 'file' widget to a FileInput rather than the default ClearableFileInput
        # so that when editing, we don't get the 'currently: ...' banner which is
        # a bit pointless here
        widgets={
            'title': forms.TextInput(),
        })


GroupDocumentPermissionFormSet = collection_member_permission_formset_factory(
    Document,
    [
        ('add_document', _("Add"), _("Add/edit documents you own")),
        ('change_document', _("Edit"), _("Edit any document")),
    ],
    'wagtaildocs/permissions/includes/document_permissions_formset.html'
)
