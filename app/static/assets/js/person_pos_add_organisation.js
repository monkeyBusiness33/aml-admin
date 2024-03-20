$(document).ready(function () {

    function organisation_type_selected_trigger(e) {
        $("#fuel_reseller_details_section").hide();
        $("#operator_details_seciton").hide();
        $("#ground_handler_details_section").hide();
        $("#nasdl_details_section").hide();

        $("#submit_btn").attr('disabled', true);

        if (typeof organisation_type_field.select2('data')[0] !== "undefined") {
            var organisation_type_id = organisation_type_field.select2('data')[0].id

            if (organisation_type_id == '1') {
                $("#operator_details_seciton").show();
                $("#id_operator_details_form_pre-contact_email").attr('required', true);
                $("#id_operator_details_form_pre-type").attr('required', true);
                $("#id_operator_details_form_pre-contact_phone").attr('required', true);
            } else {
                $("#id_operator_details_form_pre-contact_email").attr('required', false);
                $("#id_operator_details_form_pre-type").attr('required', false);
                $("#id_operator_details_form_pre-contact_phone").attr('required', false);
            }

            if (organisation_type_id == '2') {
                $("#fuel_reseller_details_section").show();
            }

            if (organisation_type_id == '3') {
                $("#ground_handler_details_section").show();
                $("#id_handler_details_form_pre-airport").attr('required', true);
                $("#id_handler_details_form_pre-handler_type").attr('required', true);
            } else {
                $("#id_handler_details_form_pre-airport").attr('required', false);
                $("#id_handler_details_form_pre-handler_type").attr('required', false);
            }

            if (organisation_type_id == '4') {
                // No actions on IPA organisation type
            }

            if (organisation_type_id == '5') {
                // No actions on Oil Conpany organisation type
            }

            if (organisation_type_id == '11') {
                // No actions on Trip Support organisation type
            }

            if (organisation_type_id == '14') {
                // No actions on Service Provider organisation type
            }

            if (organisation_type_id == '1002') {
                $("#nasdl_details_section").show();
                $("#id_nasdl_details_form_pre-type").attr('required', true);
            } else {
                $("#id_nasdl_details_form_pre-type").attr('required', false);
            }

            submit_btn.attr('disabled', false);
        }

    }
    
    $("#fuel_reseller_details_section").hide();
    $("#operator_details_seciton").hide();
    $("#ground_handler_details_section").hide();
    $("#nasdl_details_section").hide();

    const submit_btn = $("#submit_btn")
    const organisation_type_field = $('#id_organisation_type_form_pre-type')

    submit_btn.attr('disabled', true);

    // Auto-select NASDL organisation type
    if (typeof organisation_create_preselect_type_id !== "undefined") {
        // Automatically select NASDL
        let newOption = new Option('Non-Airport Service Delivery Location', '1002', true, true);
        organisation_type_field.append(newOption).trigger('change');
        // Trigger form modifier function in regard to organisation type selection change
        setTimeout(() => {
            organisation_type_selected_trigger()
        }, 150);
        // Disable editing organisation type field
        organisation_type_field.prop("disabled", true);
    }

    organisation_type_field.on('select2:select', organisation_type_selected_trigger);

    // Enable organisation type field on submitting
    submit_btn.click(function () {
        organisation_type_field.prop("disabled", false);
    });

});