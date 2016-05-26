from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.views.decorators.vary import vary_on_headers
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.encoding import force_text

from wagtail.wagtailadmin.utils import PermissionPolicyChecker

from wagtail.wagtailsearch.backends import get_search_backends

from wagtail.wagtaildocs.models import get_folder_model, get_document_model
from wagtail.wagtaildocs.forms import get_folder_form
from wagtail.wagtaildocs.permissions import permission_policy

permission_checker = PermissionPolicyChecker(permission_policy)

@permission_checker.require('add')
def add(request, add_to_folder = False):
    DocumentFolder = get_folder_model()
    DocumentFolderForm = get_folder_form(DocumentFolder)

    parent_folder = False
    if add_to_folder:
        parent_folder = get_object_or_404(DocumentFolder, id=add_to_folder)

    if request.method == 'POST':
        # Build a form for validation
        form = DocumentFolderForm(request.POST)

        if form.is_valid():
            #TODO - Check for clashing filenames
	    error = False

	    if parent_folder:
		if DocumentFolder.objects.filter(folder = parent_folder, title = form.cleaned_data['title'].strip()).count() > 0:
		    error = True
		    form._errors['title'] = "Folder already exists"
	    else:
		if DocumentFolder.objects.filter(folder__isnull = True, title = form.cleaned_data['title'].strip()).count() > 0:
		    error = True
		    form._errors['title'] = "Folder already exists"

	    if not error:
		# Save folder
		folder = DocumentFolder(
		    title = form.cleaned_data['title'].strip()
		)
		if parent_folder:
		    folder.folder = parent_folder
		folder.save()

		# Success! Send back to index or document specific folder
		response = redirect('wagtaildocs:index')
		response['Location'] += '?folder={0}'.format(folder.id)
		return response
	    else:
		return render(request, 'wagtaildocs/folder/add.html', {
		    'error_message' : 'Error adding folder',
		    'help_text': '',
		    'parent_folder' : parent_folder,
		    'form': form,
		})
        else:
            # Validation error
            return render(request, 'wagtaildocs/folder/add.html', {
                'error_message' : 'Error adding folder',
                'help_text': '',
                'parent_folder' : parent_folder,
                'form': form,
            })
    else:
        form = DocumentFolderForm()

    return render(request, 'wagtaildocs/folder/add.html', {
        'help_text': '',
        'parent_folder' : parent_folder,
        'form': form,
    })

@permission_checker.require('change')
def edit(request, folder_id):
    DocumentFolder = get_folder_model()
    DocumentFolderForm = get_folder_form(DocumentFolder)

    folder = get_object_or_404(DocumentFolder, id=folder_id)

    if request.method == 'POST':
        # Build a form for validation
        form = DocumentFolderForm(request.POST)

        if form.is_valid():
            #TODO - Check for clashing filenames
            # Save folder
            folder.title = form.cleaned_data['title']
            folder.save()

            # Success! Send back to index or document specific folder
            response = redirect('wagtaildocs:index')
            response['Location'] += '?folder={0}'.format(folder.id)
            return response
        else:
            # Validation error
            return render(request, 'wagtaildocs/folder/edit.html', {
                'error_message' : 'Error adding folder',
                'help_text': '',
                'form': form,
            })
    else:
        form = DocumentFolderForm(instance=folder)

    return render(request, 'wagtaildocs/folder/edit.html', {
        'help_text': '',
        'folder' : folder,
        'form': form,
    })

@permission_checker.require('change')
def delete(request, folder_id):
    Document = get_document_model()
    DocumentFolder = get_folder_model()
    folder = get_object_or_404(DocumentFolder, id=folder_id)

    # Make Sure folder contains no documents
    documents = Document.objects.filter(folder = folder)

    if documents.count() > 0:
	error = True
	error_text = "Cannot delete folder containing documents"
    else:
	error = False
	error_text = ""

    # Make sure folder contains no sub folders
    if not error and DocumentFolder.objects.filter(folder = folder).count() > 0:
	error = True
	error_text = "Cannot delete folder containing subfolders"

    if not error and request.method == 'POST':
	# POST if confirmation of delete

	# try find a parent folder
	parent_folder = folder.get_parent()

	# Delete folder
	folder.delete()	

	# Success! Send back to index or document specific folder
	response = redirect('wagtaildocs:index')
	if parent_folder:
	    response['Location'] += '?folder={0}'.format(parent_folder.id)
	return response	

    return render(request, 'wagtaildocs/folder/confirm_delete.html', {
	'error' : error,
        'error_text': error_text,
        'folder' : folder,
        #'form': form,
    })
