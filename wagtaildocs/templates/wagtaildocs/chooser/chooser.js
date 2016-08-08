{% load i18n %}
function(modal) {
    var searchUrl = $('form.document-search', modal.body).attr('action');

	/* currentFolder store the current folder we are browsing in, we then use
	this in the upload form to make sure the image goes into the right folder */
	var currentFolder;
	var currentFolderTitle;

    function ajaxifyLinks (context, search = false) {
        $('a.document-choice', context).click(function() {
            modal.loadUrl(this.href);
            return false;
        });

        if (!search) {
            //alert('ajaxify main pagination');
            // Main Pagination
            $('#doc-results .pagination a', context).click(function() {
                var page = this.getAttribute("data-page");
                setPage(page);
                return false;
            });
        }

        if (search) {
            //alert('ajaxify search pagination');
            // Search Pagination
            $('#doc-search-results .pagination a').click(function() {
                var page = this.getAttribute("data-page");
                setSearchPage(page);
                return false;
            });
        }

        $('ul.breadcrumb li a', context).click(function() {
            var folder = this.getAttribute("data-folder");
            var folderTitle = this.getAttribute("data-folder-title");
            setFolder(folder, folderTitle);
            return false;
        });

        $('.listing-folders a', context).click(function() {
            var folder = this.getAttribute("data-folder");
            var folderTitle = this.getAttribute("data-folder-title");
            setFolder(folder, folderTitle);
            return false;
        });
	
        $('a#switch-to-upload-tab', context).click(function() {
			// Switch to upload tab
			$('.modal a[href="#upload"]').tab('show');
			return false;
		});
    };

    function fetchResults(requestData) {
        $.ajax({
            url: searchUrl,
            data: requestData,
            success: function(data, status) {
                $('#doc-results').html(data);
                ajaxifyLinks($('#doc-results'));
				$('.modal a[href="#folders"]').tab('show'); // Switch to folders tab
            },
			error: function(){
				alert('Something went wrong');
			}
        });
    }

    function search_docs() {
        console.log("Search function");
        $.ajax({
            url: searchUrl,
            data: {
                q: $('#id_q').val(),
                collection_id: $('#collection_chooser_collection_id').val()
            },
            success: function(data, status) {
                $('#doc-search-results').html(data);
                ajaxifyLinks($('#doc-search-results'), search = true);
				//$('.modal a[href="#folders"]').tab('show'); // Switch to folders tab
            },
			error: function(){
				alert('Something went wrong');
			}
        });
        return false;
    };

    function fetchFolders(requestData) {
        $.ajax({
            url: searchUrl,
            data: requestData,
            success: function(data, status) {
                $('#folder-results-wrapper').html(data);
                ajaxifyLinks($('#folder-results-wrapper'));
            },
			error: function(){
				alert('Something went wrong');
			}
        });
    }

    function setPage(page) {
        if($('#id_q').val().length){
            dataObj = {q: $('#id_q').val(), p: page};
        }else{
            dataObj = {p: page};
        }

        $.ajax({
            url: searchUrl,
            data: dataObj,
            success: function(data, status) {
                $('#doc-results').html(data);
                ajaxifyLinks($('#doc-results'));
            }
        });
        return false;
    }

    function setSearchPage(page) {
        if($('#id_q').val().length){
            dataObj = {q: $('#id_q').val(), p: page};
        }else{
            dataObj = {p: page};
        }

        $.ajax({
            url: searchUrl,
            data: dataObj,
            success: function(data, status) {
                $('#doc-search-results').html(data);
                ajaxifyLinks($('#doc-search-results'), search = true);
            }
        });
        return false;
    }

	function updateLabels(){
		// Folder title label
		if (currentFolderTitle){
			$('.label-folder-title').html(currentFolderTitle);
		} else {
			$('.label-folder-title').html('Root');	
		}
	}

    function setFolder(folder, folderTitle) {
		currentFolder = folder;
		currentFolderTitle = folderTitle;
		updateLabels();
		// Set currentFolder in form
		$('form.document-upload input#id_folder').val(folder)
        params = {folder: folder};
		//TODO - reset currentTag or query?
        fetchResults(params);
		// Second query to get folders
        params = {folder: folder, folders_only: '1'};
        fetchFolders(params);
        return false;
    }

    ajaxifyLinks(modal.body);

    $('form.document-upload', modal.body).submit(function() {
        var formdata = new FormData(this);

        $.ajax({
            url: this.action,
            data: formdata,
            processData: false,
            contentType: false,
            type: 'POST',
            dataType: 'text',
            success: function(response){
                modal.loadResponseText(response);
            },
            error: function(response, textStatus, errorThrown) {
                {% trans "Server Error" as error_label %}
                {% trans "Report this error to your webmaster with the following information:" as error_message %}
                message = '{{ error_message|escapejs }}<br />' + errorThrown + ' - ' + response.status;
                $('#upload').append(
                    '<div class="help-block help-critical">' +
                    '<strong>{{ error_label|escapejs }}: </strong>' + message + '</div>');
            }
        });

        return false;
    });

    $('form.document-search', modal.body).submit(search_docs);

    $('#id_q').on('input', function() {
        clearTimeout($.data(this, 'timer'));
        var wait = setTimeout(search_docs, 200);
        $(this).data('timer', wait);
    });

    $('#collection_chooser_collection_id').change(search_docs);

    {% url 'wagtailadmin_tag_autocomplete' as autocomplete_url %}
    $('#id_tags', modal.body).tagit({
        autocomplete: {source: "{{ autocomplete_url|addslashes }}"}
    });
}
