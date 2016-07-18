from __future__ import absolute_import, unicode_literals

import json

from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render

from wagtail.utils.pagination import paginate
from wagtail.wagtailadmin.forms import SearchForm
from wagtail.wagtailadmin.modal_workflow import render_modal_workflow
from wagtail.wagtailadmin.utils import PermissionPolicyChecker
from wagtail.wagtailcore.models import Collection
from wagtail.wagtaildocs.forms import get_document_form, get_folder_form
from wagtail.wagtaildocs.models import get_document_model, get_folder_model
from wagtail.wagtaildocs.permissions import permission_policy
from wagtail.wagtailsearch import index as search_index

permission_checker = PermissionPolicyChecker(permission_policy)


def get_document_json(document):
    """
    helper function: given a document, return the json to pass back to the
    chooser panel
    """

    return json.dumps({
        'id': document.id,
        'title': document.title,
        'url': document.url,
        'edit_link': reverse('wagtaildocs:edit', args=(document.id,)),
    })


def chooser(request):
    Document = get_document_model()
    DocumentFolder = get_folder_model()

    if permission_policy.user_has_permission(request.user, 'add'):
        DocumentForm = get_document_form(Document)
        uploadform = DocumentForm(user=request.user)
        DocumentFolderForm = get_folder_form(DocumentFolder)
    else:
        uploadform = None

    documents = Document.objects.filter(folder__isnull = True).order_by('-created_at')

    # Check if folders_only
    folders_only = request.GET.get('folders_only')
    if folders_only:
        folders_only = True
    else:
        folders_only = False

    # Filter by folder
    folders = DocumentFolder.objects.filter(folder__isnull = True)
    current_folder = None
    folder_id = request.GET.get('folder')
    if folder_id:
        try:
            current_folder = DocumentFolder.objects.get(id=folder_id)
            documents = Document.objects.filter(folder=current_folder)
        except (ValueError, DocumentFolder.DoesNotExist):
            pass

    q = None
    is_searching = False
    if (
        'q' in request.GET or
        'p' in request.GET or
        'collection_id' in request.GET or
        'folder' in request.GET
    ):
        if not current_folder:
            # Make sure we are not in a folder
            documents = Document.objects.all()

        collection_id = request.GET.get('collection_id')
        if collection_id:
            documents = documents.filter(collection=collection_id)

        searchform = SearchForm(request.GET)
        if searchform.is_valid():
            q = searchform.cleaned_data['q']

            documents = documents.search(q)
            is_searching = True
        else:
            documents = documents.order_by('-created_at')
            is_searching = False

        # Pagination
        paginator, documents = paginate(request, documents, per_page=10)

        if not folders_only:
            return render(request, "wagtaildocs/chooser/results.html", {
                'documents': documents,
                'folders' : folders,
                'current_folder' : current_folder,
                'query_string': q,
                'is_searching': is_searching,
            })
        else:
            return render(request, "wagtaildocs/chooser/folders.html", {
                'documents': documents,
                'folders' : folders,
                'current_folder' : current_folder,
                'query_string': q,
                'is_searching': is_searching,
            })
    else:
        searchform = SearchForm()

        collections = Collection.objects.all()
        if len(collections) < 2:
            collections = None

        documents = Document.objects.order_by('-created_at')
        paginator, documents = paginate(request, documents, per_page=10)

    return render_modal_workflow(request, 'wagtaildocs/chooser/chooser.html', 'wagtaildocs/chooser/chooser.js', {
        'documents': documents,
        'folders' : folders,
        'current_folder' : current_folder,
        'uploadform': uploadform,
        'searchform': searchform,
        'collections': collections,
        'is_searching': False,
    })


def document_chosen(request, document_id):
    document = get_object_or_404(get_document_model(), id=document_id)

    return render_modal_workflow(
        request, None, 'wagtaildocs/chooser/document_chosen.js',
        {'document_json': get_document_json(document)}
    )


@permission_checker.require('add')
def chooser_upload(request):
    Document = get_document_model()
    DocumentForm = get_document_form(Document)

    if request.method == 'POST':
        document = Document(uploaded_by_user=request.user)
        form = DocumentForm(request.POST, request.FILES, instance=document, user=request.user)

        if form.is_valid():
            form.save()

            # Reindex the document to make sure all tags are indexed
            search_index.insert_or_update_object(document)

            return render_modal_workflow(
                request, None, 'wagtaildocs/chooser/document_chosen.js',
                {'document_json': get_document_json(document)}
            )
    else:
        form = DocumentForm(user=request.user)

    documents = Document.objects.order_by('title')

    return render_modal_workflow(
        request, 'wagtaildocs/chooser/chooser.html', 'wagtaildocs/chooser/chooser.js',
        {'documents': documents, 'uploadform': form}
    )
