$(document).ready(function () {
    let asyncSuccessMessage = "<script>notyf.open({ type: 'success',message:'Organisation has been created'});</script>"

    function organisation_create_button(e) {
        // Disable old event listener on the button if it exists
        $(".modal_button_async").each(function () {
            $(this).modalForm().off()
        });

        if (organisation_create_url == '') {
            $(".organisation_create_btn").attr('disabled', true);
        } else {
            // Init modal button
            function organisationCreateModalForm() {
                $(".organisation_create_btn").each(function () {
                    $(this).modalForm({
                        modalID: "#modal-xl",
                        formURL: organisation_create_url,
                        errorClass: ".is-invalid",
                        asyncUpdate: true,
                        asyncSettings: {
                            closeOnSubmit: true,
                            successMessage: asyncSuccessMessage,
                            dataUrl: ping_url,
                            dataElementId: "#none",
                            dataKey: "data",
                            addModalFormFunction: organisationCreateModalForm
                        }
                    });
                });
            }
            organisationCreateModalForm();
        }

    }
    organisation_create_button()

});