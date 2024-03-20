$(document).ready(function () {

    // Submit form via ajax
    function load_role_permissions_grant_buttons(e) {
        let serializedData = ops_portal_settings_form.serialize();
        $.ajax({
            type: 'POST',
            url: ops_settings_form_url,
            data: serializedData,
            success: function (response) {
                notyf.open({ type: 'success', message: response.message })
            },
        })
    }

    // Global variables
    const ops_portal_settings_form = $('#ops_portal_settings_form')

    // Form changes processing
    if (ops_portal_settings_form.length) {
        ops_portal_settings_form.change(function () {
            load_role_permissions_grant_buttons()
        });
    }


});