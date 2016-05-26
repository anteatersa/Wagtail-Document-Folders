from django.conf.urls import url
from wagtail.wagtaildocs.views import documents, chooser, multiple, folders


urlpatterns = [
    url(r'^$', documents.index, name='index'),
    url(r'^add/$', documents.add, name='add'),
    url(r'^edit/(\d+)/$', documents.edit, name='edit'),
    url(r'^delete/(\d+)/$', documents.delete, name='delete'),

    url(r'^multiple/add/$', multiple.add, name='add_multiple'),
    url(r'^multiple/(\d+)/$', multiple.edit, name='edit_multiple'),
    url(r'^multiple/(\d+)/delete/$', multiple.delete, name='delete_multiple'),

    url(r'^folder/add/$', folders.add, name='add_folder'),
    url(r'^folder/add/(\d+)/$', folders.add, name='add_folder_to_folder'),
    url(r'^folder/delete/(\d+)/$', folders.delete, name='delete_folder'),
    url(r'^folder/(\d+)/$', folders.edit, name='edit_folder'),

    url(r'^chooser/$', chooser.chooser, name='chooser'),
    url(r'^chooser/(\d+)/$', chooser.document_chosen, name='document_chosen'),
    url(r'^chooser/upload/$', chooser.chooser_upload, name='chooser_upload'),
    url(r'^usage/(\d+)/$', documents.usage, name='document_usage'),
]
