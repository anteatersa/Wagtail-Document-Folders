from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError

from wagtail.wagtailadmin.utils import PermissionPolicyChecker
from wagtail.wagtaildocs.models import get_folder_model, get_document_model
from wagtail.wagtaildocs.forms import get_folder_form
from wagtail.wagtaildocs.permissions import permission_policy

permission_checker = PermissionPolicyChecker(permission_policy)
DocumentFolder = get_folder_model()
Document = get_document_model()
DocumentFolderForm = get_folder_form(DocumentFolder)


@permission_checker.require('add')
def add(request, add_to_folder=False):

    parent_folder = False
    if add_to_folder:
        parent_folder = get_object_or_404(DocumentFolder, id=add_to_folder)

    if request.method == 'POST':
        # Build a form for validation
        form = DocumentFolderForm(request.POST)
        error = True

        if form.is_valid():
            error = False

            folder = DocumentFolder(
                title=form.cleaned_data['title'].strip()
            )
            if parent_folder:
                folder.folder = parent_folder

            try:
                # Check if the folder is present in the DB or physically present in the OS
                folder.validate_folder()
            except ValidationError as e:
                error = True
                form._errors['title'] = e.message
            else:
                # Save folder
                folder.save()

        if not error:
            # Success! Send back to index or document specific folder
            response = redirect('wagtaildocs:index')
            response['Location'] += '?folder={0}'.format(folder.id)
            return response
        else:
            # Validation error
            return render(request, 'wagtaildocs/folder/add.html', {
                'error_message': 'Error adding folder',
                'help_text': '',
                'parent_folder': parent_folder,
                'form': form,
            })

    else:
        form = DocumentFolderForm()

        return render(request, 'wagtaildocs/folder/add.html', {
            'help_text': '',
            'parent_folder': parent_folder,
            'form': form,
        })


@permission_checker.require('change')
def edit(request, folder_id):
    folder = get_object_or_404(DocumentFolder, id=folder_id)

    if request.method == 'POST':
        # Build a form for validation
        form = DocumentFolderForm(request.POST)

        if form.is_valid():

            folder.title = form.cleaned_data['title']

            try:
                # Check if the folder is present in the DB or physically present in the OS
                folder.validate_folder()
            except ValidationError as e:
                form._errors['title'] = e.message
                return render(request, 'wagtaildocs/folder/edit.html', {
                    'error_message': 'Error adding folder',
                    'help_text': '',
                    'form': form,
                })

            folder.save()

            # Success! Send back to index or document specific folder
            response = redirect('wagtaildocs:index')
            response['Location'] += '?folder={0}'.format(folder.id)
            return response

        else:
            # Validation error
            return render(request, 'wagtaildocs/folder/edit.html', {
                'error_message': 'Error adding folder',
                'help_text': '',
                'form': form,
            })
    else:
        form = DocumentFolderForm(instance=folder)

    return render(request, 'wagtaildocs/folder/edit.html', {
        'help_text': '',
        'folder': folder,
        'form': form,
    })


@permission_checker.require('change')
def delete(request, folder_id):
    folder = get_object_or_404(DocumentFolder, id=folder_id)

    if request.method == 'POST':
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
        'folder': folder,
    })
