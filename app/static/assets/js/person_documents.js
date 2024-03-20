$(document).on('click', '.document-file-delete', function (e) {
    let file_id = $(this).data('file-id')
    let file_delete_url = $(this).data('form-url')

    swalWithBootstrapButtons.fire({
        icon: 'error',
        title: 'Delete file?',
        text: 'This action will delete file from document.',
        showCancelButton: true,
        confirmButtonText: "Yes, delete it!",
        cancelButtonText: 'No, go back!',
    }).then(function (result) {
        if (result.value) {
            $.ajax({
                type: 'POST',
                url: file_delete_url,
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'sessionid': getCookie('sessionid')
                },
                success: function (response) {
                    if (response.success === 'true') {
                        $('#document_file_row_' + file_id).remove();
                        swalWithBootstrapButtons.fire(
                            'Deleted',
                            'The file has been deleted.',
                            'success'
                        );
                    }
                },
            });
        } else if (result.dismiss === Swal.DismissReason.cancel) {
        }
    });

});